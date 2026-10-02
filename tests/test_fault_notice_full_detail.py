from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.atp_reader import ATP_ANALYSIS_FIELDS
from mmis_connector.fault_notices.full_detail import FaultNoticeFullDetailReader
from mmis_connector.fault_notices.linked_work_orders import FIELDS as LINKED_FIELDS
from mmis_connector.fault_notices.reader import ANALYSIS_FIELDS
from mmis_connector.fault_notices.repair_work_orders import FIELDS as REPAIR_FIELDS
from mmis_connector.parser import parse_fault_notice_basic_info
from tools.mmis_development.query_fault_notice_full_detail import execute


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-02_query-fault-notice-basic-information\dom"
    r"\2026-10-02T065515-168.html"
)


def _basic_info() -> str:
    fields = (
        ("通報號", "1150210-36"), ("事故等級", "A"),
        ("狀態", "處理完成"), ("發生日期", ""),
        ("車次", "2193"), ("車組/車號", "EM9351"),
    )
    return "".join(
        f'<label for="b{i}">{name}:</label>'
        f'<input id="b{i}" value="{value}"'
        + (' title="2026/09/09"' if name == "發生日期" else "")
        + ">"
        for i, (name, value) in enumerate(fields)
    )


def _detail(checked: bool) -> str:
    status = "已勾選" if checked else "未勾選"
    source = "cb_checkedreadonly.gif" if checked else "cb_uncheckedreadonly.gif"
    attribute = ' checked="checked"' if checked else ""
    return (
        f'<img alt="ATP故障： {status}" src="{source}"{attribute}>'
        f'{_basic_info()}'
        '<li id="tracking" ctype="tab"><a title="故障追蹤"></a></li>'
        '<li id="analysis" ctype="tab"><a title="故障分析"></a></li>'
    )


def _table(
    summary: str, prefix: str, fields: tuple[str, ...], number: str,
    *, start: int = 1, total: int = 1,
) -> str:
    headers = "".join(
        f'<span id="{prefix}_ttrow_[C:{i}]_ttitle-lb">{field}</span>'
        for i, field in enumerate(fields, 1)
    )
    values = (number,) + ("",) * (len(fields) - 1)
    cells = "".join(
        f'<td id="{prefix}_tdrow_[C:{i}]-c[R:0]"><span title="{value}">{value}</span></td>'
        for i, value in enumerate(values, 1)
    )
    next_control = (
        f'<a id="{prefix}-ti7"><img id="{prefix}-ti7_img" src="tablebtn_next_on.gif"></a>'
        if start < total else ""
    )
    return (
        f'<label id="{prefix}-lb3" class="tCount">{start} - {start}/{total}</label>'
        f'{next_control}'
        f'<table summary="{summary}">{headers}'
        f'<tr id="{prefix}_tbod_tdrow-tr[R:0]">{cells}</tr></table>'
    )


def _tracking() -> str:
    return (
        _table("檢視所有段檢修工單", "linked", LINKED_FIELDS, "115-C1-35820")
        + _table("查修工單", "repair", REPAIR_FIELDS, "115-CA-40035")
    )


def _analysis() -> str:
    fields = "".join(
        f'<label for="a{i}">{name}:</label><textarea id="a{i}">{name}</textarea>'
        for i, name in enumerate(ANALYSIS_FIELDS)
    )
    return fields + '<li id="atp" ctype="tab"><a title="故障分析-ATP"></a></li>'


def _atp() -> str:
    return "".join(
        f'<label for="p{i}">{name}:</label><input id="p{i}" value="{name}">'
        for i, name in enumerate(ATP_ANALYSIS_FIELDS)
    )


@pytest.mark.parametrize("checked", [False, True])
def test_full_detail_reads_both_order_tables_and_conditional_atp(
    monkeypatch: pytest.MonkeyPatch, checked: bool
) -> None:
    reader = FaultNoticeFullDetailReader(SimpleNamespace(state=STATE))
    detail_calls: list[str] = []

    def load_detail(notice: str) -> tuple[PageState, str]:
        detail_calls.append(notice)
        return STATE, _detail(checked)

    monkeypatch.setattr(reader, "_load_exact_detail", load_detail)
    responses = iter((_tracking(), _analysis(), _atp()) if checked else (_tracking(), _analysis()))
    events: list[tuple[str, int]] = []

    def post(**kwargs: object) -> str:
        events.append((str(kwargs["target_id"]), int(kwargs["xhr_seq"])))
        return next(responses)

    monkeypatch.setattr(reader, "_post_event", post)
    result = reader.run("1150210-36")

    assert detail_calls == ["1150210-36"]
    assert events == ([("tracking", 3), ("analysis", 4), ("atp", 5)] if checked
                      else [("tracking", 3), ("analysis", 4)])
    assert list(result) == [
        "通報號", "事故等級", "狀態", "發生日期", "車次", "車組/車號",
        "是ATP故障", "段修工單", "CA查修工單", "故障分析", "ATP故障分析"
    ]
    assert result["通報號"] == "1150210-36"
    assert result["發生日期"] == "2026/09/09"
    assert "查詢故障通報基本資料" not in result
    assert "事故現象" not in result
    assert result["是ATP故障"] is checked
    assert result["段修工單"][0]["工作單"] == "115-C1-35820"
    assert result["CA查修工單"][0]["工作單"] == "115-CA-40035"
    assert result["故障分析"] == {name: name for name in ANALYSIS_FIELDS}
    assert result["ATP故障分析"] == (
        {name: name for name in ATP_ANALYSIS_FIELDS} if checked else None
    )


def test_bad_notice_is_rejected_before_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tools.mmis_development.query_fault_notice_full_detail.MMISSession",
        lambda config: pytest.fail("login should not start"),
    )
    with pytest.raises(MMISClientError, match="通報號必須符合"):
        execute(["bad-notice"])


def test_both_tables_paginate_before_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = FaultNoticeFullDetailReader(SimpleNamespace(state=STATE))
    monkeypatch.setattr(reader, "_load_exact_detail", lambda notice: (STATE, _detail(False)))
    first_page = (
        _table("檢視所有段檢修工單", "linked", LINKED_FIELDS,
               "115-C1-35820", total=2)
        + _table("查修工單", "repair", REPAIR_FIELDS,
                 "115-CA-40035", total=2)
    )
    responses = iter((
        first_page,
        _table("檢視所有段檢修工單", "linked", LINKED_FIELDS,
               "115-C1-35821", start=2, total=2),
        _table("查修工單", "repair", REPAIR_FIELDS,
               "115-CA-40036", start=2, total=2),
        _analysis(),
    ))
    events: list[tuple[str, int]] = []

    def post(self: object, **kwargs: object) -> str:
        events.append((str(kwargs["target_id"]), int(kwargs["xhr_seq"])))
        return next(responses)

    monkeypatch.setattr("mmis_connector.events.MaximoEventClient.post", post)
    result = reader.run("1150210-36")

    assert events == [
        ("tracking", 3), ("linked-ti7", 4), ("repair-ti7", 5), ("analysis", 6)
    ]
    assert [row["工作單"] for row in result["段修工單"]] == [
        "115-C1-35820", "115-C1-35821"
    ]
    assert [row["工作單"] for row in result["CA查修工單"]] == [
        "115-CA-40035", "115-CA-40036"
    ]


def test_basic_info_accepts_equal_duplicate_labels_and_rejects_conflicts() -> None:
    html = _basic_info() + '<label for="second-train">車次:</label><input id="second-train" value="2193">'
    assert parse_fault_notice_basic_info(html, expected_notice="1150210-36")["車次"] == "2193"
    with pytest.raises(MMISClientError, match="車次.*不一致"):
        parse_fault_notice_basic_info(
            html.replace('id="second-train" value="2193"',
                         'id="second-train" value="9999"'),
            expected_notice="1150210-36",
        )
    with pytest.raises(MMISClientError, match="通報號與輸入不相符"):
        parse_fault_notice_basic_info(html, expected_notice="1150210-37")
    with pytest.raises(MMISClientError, match="事故等級.*缺失"):
        parse_fault_notice_basic_info(
            html.replace('<label for="b1">事故等級:</label>', ""),
            expected_notice="1150210-36",
        )


def test_basic_info_date_uses_dojo_timestamp_when_title_is_absent() -> None:
    html = _basic_info().replace(
        'title="2026/09/09"', 'dojovalue="1788883200000"'
    )
    assert parse_fault_notice_basic_info(
        html, expected_notice="1150210-36"
    )["發生日期"] == "2026/09/09"


@pytest.mark.skipif(not RECORDED_DOM.is_file(), reason="local recording unavailable")
def test_recorded_basic_information() -> None:
    basic_info = parse_fault_notice_basic_info(
        RECORDED_DOM.read_text(encoding="utf-8"),
        expected_notice="1150910-14",
    )
    assert basic_info == {
        "通報號": "1150910-14", "事故等級": "A", "狀態": "處理完成",
        "發生日期": "2026/09/09", "車次": "2193", "車組/車號": "EM9351",
    }
