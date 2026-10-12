from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.daily_inspection.reader import (
    DailyInspectionInspectionRecordReader,
    parse_daily_inspection_basic_info,
    parse_daily_inspection_linked_fault_notices,
)
from tools.mmis_development import query_daily_inspection_work_order_inspection_records as tool


STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-07_query-daily-inspection-work-order-details\dom"
    r"\2026-10-07T065114-823.html"
)
BASIC_RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-12_query-daily-inspection-work-order-basic-information\dom"
    r"\2026-10-12T054040-151.html"
)
FAULT_RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-12_query-fault-notices-linked-to-daily-inspection-work-order\dom"
    r"\2026-10-12T060626-365.html"
)
PERSONNEL_RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-12_query-daily-inspection-work-order-maintenance-personnel-list\dom"
    r"\2026-10-12T063348-932.html"
)
BASIC_VALUES = {
    "工作單": "115-1A-71815",
    "車組/車號": "EMU937",
    "檢修日期": "2026/10/06",
    "車次": "1243",
    "工作單狀態": "核簽中",
    "開單人姓名": "系統管理人員",
    "開單日期": "2026/09/26 01:15",
}


def _basic_info() -> str:
    return "".join(
        f'<label for="basic-{index}">{field}:</label>'
        f'<input id="basic-{index}" value="{value}">'
        for index, (field, value) in enumerate(BASIC_VALUES.items())
    )


def _tab(title: str, target: str) -> str:
    return f'<li ctype="tab" id="{target}"><a title="{title}">{title}</a></li>'


def _fault_notices(*, count: int = 0, total: int | None = None) -> str:
    headers = "".join(
        f'<span id="fault_ttrow_[C:{index}]_ttitle-lb">{field}</span>'
        for index, field in enumerate(("故障通報號", "發生日期", "車組/車號", "故障現象"))
    )
    rows = "".join(
        f'<tr id="fault_tbod_tdrow-tr[R:{index}]">'
        f'<td id="fault_tdrow_[C:0]-c[R:{index}]"><span title="1151006-32">1151006-32</span></td>'
        f'<td id="fault_tdrow_[C:1]-c[R:{index}]"><span title="2026/10/06">2026/10/06</span></td>'
        f'<td id="fault_tdrow_[C:2]-c[R:{index}]"><span title="EMU937">EMU937</span></td>'
        f'<td id="fault_tdrow_[C:3]-c[R:{index}]"><span title="第一行">第一行</span></td>'
        '</tr>'
        for index in range(count)
    )
    total = count if total is None else total
    page = f'<label id="fault-lb3" class="tCount">1 - {count}/{total}</label>' if count else ""
    return f'{page}<table id="fault_tbod-tbd" summary="故障通報管理">{headers}{rows}</table>'


NOTE_FIELDS = (
    "車組/車號", "故障類別", "故障類別說明", "故障現象", "故障原因",
    "處置措施", "材料編號(PA)", "員工代號", "人員姓名",
)
PERSONNEL_FIELDS = ("人員群組", "工作角色", "員工代號", "姓名", "單位")


def _personnel(rows: list[tuple[str, ...]], *, start: int = 1,
               total: int | None = None, next_page: bool = False) -> str:
    total = len(rows) if total is None else total
    count = f"{start} - {start + len(rows) - 1}/{total}" if rows else "0 - 0/0"
    headers = "".join(
        f'<span id="person_ttrow_[C:{index}]_ttitle-lb">{field}</span>'
        for index, field in enumerate(PERSONNEL_FIELDS)
    )
    body = "".join(
        f'<tr id="person_tbod_tdrow-tr[R:{row_index}]">'
        + "".join(
            f'<td id="person_tdrow_[C:{index}]-c[R:{row_index}]">'
            f'<input id="person_tdrow_[C:{index}]_txt-tb[R:{row_index}]" value="{value}"></td>'
            for index, value in enumerate(values)
        ) + "</tr>"
        for row_index, values in enumerate(rows)
    )
    next_button = (
        '<a id="person-ti7"><img id="person-ti7_img" src="tablebtn_next_on.gif"></a>'
        if next_page else ""
    )
    return (
        f'<label class="tCount" id="person-lb3">{count}</label>{next_button}'
        f'<table id="person_tbod-tbd" summary="檢修人員">{headers}{body}</table>'
    )


def _notes(rows: list[tuple[str, ...]], *, start: int = 1,
           total: int | None = None, next_page: bool = False) -> str:
    total = len(rows) if total is None else total
    count = f"{start} - {start + len(rows) - 1}/{total}" if rows else "0 - 0/0"
    headers = "".join(
        f'<span id="note_ttrow_[C:{index}]_ttitle-lb">{field}</span>'
        for index, field in enumerate(NOTE_FIELDS, 1)
    )
    body = "".join(
        f'<tr id="note_tbod_tdrow-tr[R:{row_index}]" currentrow="{str(row_index == 0).lower()}">'
        + "".join(
            f'<td id="note_tdrow_[C:{index}]-c[R:{row_index}]">'
            f'<input id="note_tdrow_[C:{index}]_txt-tb[R:{row_index}]" value="{value}"></td>'
            for index, value in enumerate(values, 1)
        ) + "</tr>"
        for row_index, values in enumerate(rows)
    )
    next_button = (
        '<a id="note-ti7"><img id="note-ti7_img" src="tablebtn_next_on.gif"></a>'
        if next_page else ""
    )
    return (
        f'<label class="tCount" id="note-lb3">{count}</label>{next_button}'
        f'<table id="note_tbod-tbd" summary="紀事(備註)清單">{headers}{body}</table>'
    )


def _table(
    remarks: list[str], *, start: int = 1, total: int | None = None,
    next_page: bool = False,
) -> str:
    total = len(remarks) if total is None else total
    headers = "".join(
        f'<span id="work_ttrow_[C:{column}]_ttitle-lb">{name}</span>'
        for column, name in ((3, "裝置名稱"), (6, "回報結果"), (8, "備註"))
    )
    rows = "".join(
        f'<tr id="work_tbod_tdrow-tr[R:{i}]">'
        f'<td id="work_tdrow_[C:3]-c[R:{i}]"><span title="裝置{i}">裝置{i}</span></td>'
        f'<td id="work_tdrow_[C:6]-c[R:{i}]"><span title="異常">異常</span></td>'
        f'<td id="work_tdrow_[C:8]-c[R:{i}]"><input id="work_tdrow_[C:8]_txt-tb[R:{i}]" value="{remark}"></td>'
        "</tr>"
        for i, remark in enumerate(remarks)
    )
    count = f"{start} - {start + len(remarks) - 1}/{total}" if remarks else "0 - 0/0"
    next_button = (
        '<a id="work-ti7"><img id="work-ti7_img" src="tablebtn_next_on.gif"></a>'
        if next_page
        else ""
    )
    return (
        f'<label id="work-lb3" class="tCount">{count}</label>{next_button}'
        '<table id="work_tbod-tbd" summary="工作單的作業 123">'
        f"{headers}{rows}</table>"
    )


def _run(
    monkeypatch: pytest.MonkeyPatch, response: str, *, fault_count: int = 0
) -> tuple[dict[str, Any], list[str]]:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    monkeypatch.setattr(
        reader,
        "open_detail",
        lambda number: (
            "115-1A-71815", _basic_info() + _fault_notices(count=fault_count)
            + _tab("檢修回報", "report-tab") + _tab("檢修人員(單位)", "personnel-tab")
        ),
    )
    calls: list[str] = []

    def post_event(**kwargs: Any) -> str:
        calls.append(kwargs["target_id"])
        if len(calls) == 1:
            return _personnel([])
        if len(calls) == 2:
            return _tab("檢修記錄", "records-tab") + _notes([])
        return response

    monkeypatch.setattr(reader, "_post_event", post_event)
    return reader.run("115-1A-71815"), calls


def test_reads_only_nonempty_remarks_and_uses_both_tabs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run(monkeypatch, _table(["", " 洩漏 ", "  ", "停用"]))
    assert calls == ["personnel-tab", "report-tab", "records-tab"]
    assert result["count"] == 2
    assert result["records"] == [
        {"裝置名稱": "裝置1", "回報結果": "異常", "備註": "洩漏"},
        {"裝置名稱": "裝置3", "回報結果": "異常", "備註": "停用"},
    ]
    assert result["important_notes"] == {"count": 0, "records": []}
    assert result["linked_fault_notices"] == {"count": 0, "records": []}


def test_all_empty_remarks_are_successful_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run(monkeypatch, _table(["", "  "]))
    assert result["success"] is True
    assert result["count"] == 0
    assert result["records"] == []


def test_run_includes_linked_fault_notice_from_same_detail_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run(monkeypatch, _table([]), fault_count=1)
    assert result["linked_fault_notices"] == {
        "count": 1,
        "records": [{
            "故障通報號": "1151006-32", "發生日期": "2026/10/06",
            "車組/車號": "EMU937", "故障現象": "第一行",
        }],
    }
    assert calls == ["personnel-tab", "report-tab", "records-tab"]


def test_reads_all_pages_without_losing_order(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    monkeypatch.setattr(
        reader,
        "open_detail",
        lambda number: (
            "115-1A-71815", _basic_info() + _fault_notices()
            + _tab("檢修回報", "report-tab") + _tab("檢修人員(單位)", "personnel-tab")
        ),
    )
    responses = iter(
        [
            _personnel([]),
            _tab("檢修記錄", "records-tab") + _notes([]),
            _table(["第一頁"], total=2, next_page=True),
            _table(["第二頁"], start=2, total=2),
        ]
    )
    targets: list[str] = []

    def post_event(**kwargs: Any) -> str:
        targets.append(kwargs["target_id"])
        return next(responses)

    monkeypatch.setattr(reader, "_post_event", post_event)
    result = reader.run("115-1A-71815")
    assert targets == ["personnel-tab", "report-tab", "records-tab", "work-ti7"]
    assert [record["備註"] for record in result["records"]] == ["第一頁", "第二頁"]


def test_empty_source_table_is_successful(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _run(monkeypatch, _table([]))
    assert result["count"] == 0
    assert result["records"] == []
    assert result["maintenance_personnel"] == {"count": 0, "records": []}


def test_important_notes_read_nine_fields_and_all_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    first = ("EMU718", "1", "牽引", "異音", "磨耗", "更換", "PA1", "E1", "王員")
    second = ("EMU718", "2", "軔機", "漏氣", "接頭", "修復", "", "E2", "李員")
    monkeypatch.setattr(
        reader, "_post_event", lambda **kwargs: _notes([second], start=2, total=2)
    )
    records, next_seq = reader._read_important_notes(
        _notes([first], total=2, next_page=True), state=STATE, xhr_seq=7
    )
    assert records == [dict(zip(NOTE_FIELDS, first)), dict(zip(NOTE_FIELDS, second))]
    assert next_seq == 8


def test_important_notes_append_selected_row_supplement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    values = ("EMU718", "1", "牽引", "其它問題", "磨耗", "更換", "", "E1", "王員")
    response = _notes([values]) + (
        '<table id="note_tdet-chld"><label for="extra-ta">其它故障現象:</label>'
        '<textarea id="extra-ta">齒輪箱異音</textarea></table>'
    )
    monkeypatch.setattr(
        reader, "_post_event", lambda **kwargs: pytest.fail("不應切換已選取資料列")
    )
    records, _ = reader._read_important_notes(response, state=STATE, xhr_seq=7)
    assert records[0]["故障現象"] == "其它問題：齒輪箱異音"


def test_important_notes_reject_missing_table() -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    with pytest.raises(MMISClientError, match="紀事"):
        reader._read_important_notes("<div>缺少表格</div>", state=STATE, xhr_seq=7)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ("<div>缺少表格</div>", "表格"),
        (_table(["備註"], total=2), "下一頁"),
        (_table(["備註"], next_page=True), "末頁"),
    ],
)
def test_rejects_missing_or_incomplete_table(
    monkeypatch: pytest.MonkeyPatch, response: str, message: str
) -> None:
    with pytest.raises(MMISClientError, match=message):
        _run(monkeypatch, response)


@pytest.mark.skipif(not RECORDED_DOM.exists(), reason="本機未提供檢修記錄錄製 DOM")
def test_recorded_dom_yields_one_of_26_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _run(monkeypatch, RECORDED_DOM.read_text(encoding="utf-8"))
    assert result["count"] == 1
    assert result["records"] == [
        {
            "裝置名稱": "牽引馬達及齒輪箱組",
            "回報結果": "異常",
            "備註": "EM9373#4齒輪箱洩漏大，禁用。",
        }
    ]


@pytest.mark.skipif(not BASIC_RECORDED_DOM.exists(), reason="本機未提供日檢基本資料錄製 DOM")
def test_recorded_basic_information() -> None:
    assert parse_daily_inspection_basic_info(
        BASIC_RECORDED_DOM.read_text(encoding="utf-8"),
        expected_work_order="115-1A-71815",
    ) == BASIC_VALUES


@pytest.mark.skipif(not FAULT_RECORDED_DOM.exists(), reason="本機未提供勾稽通報錄製 DOM")
def test_recorded_linked_fault_notice() -> None:
    linked = parse_daily_inspection_linked_fault_notices(
        FAULT_RECORDED_DOM.read_text(encoding="utf-8")
    )
    assert linked["count"] == 1
    assert linked["records"][0]["故障通報號"] == "1151006-32"
    assert set(linked["records"][0]) == {"故障通報號", "發生日期", "車組/車號", "故障現象"}


def test_linked_fault_notice_rejects_incomplete_page() -> None:
    with pytest.raises(MMISClientError, match="不完整資料"):
        parse_daily_inspection_linked_fault_notices(_fault_notices(count=1, total=2))


@pytest.mark.skipif(not PERSONNEL_RECORDED_DOM.exists(), reason="本機未提供檢修人員錄製 DOM")
def test_recorded_maintenance_personnel_has_seven_rows() -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    result, _ = reader._read_maintenance_personnel(
        PERSONNEL_RECORDED_DOM.read_text(encoding="utf-8"), state=STATE, xhr_seq=9
    )
    assert result["count"] == 7
    assert len(result["records"]) == 7
    assert all(tuple(row) == PERSONNEL_FIELDS for row in result["records"])
    assert all(row["員工代號"] for row in result["records"])


def test_maintenance_personnel_reads_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    first = ("檢查室", "檢修人員", "E1", "甲", "新竹機務段")
    second = ("檢查室", "檢修人員", "E2", "乙", "新竹機務段")
    targets: list[str] = []

    def post_event(**kwargs: Any) -> str:
        targets.append(kwargs["target_id"])
        return _personnel([second], start=2, total=2)

    monkeypatch.setattr(reader, "_post_event", post_event)
    result, next_seq = reader._read_maintenance_personnel(
        _personnel([first], total=2, next_page=True), state=STATE, xhr_seq=9
    )
    assert result == {
        "count": 2,
        "records": [
            dict(zip(PERSONNEL_FIELDS, first)),
            dict(zip(PERSONNEL_FIELDS, second)),
        ],
    }
    assert targets == ["person-ti7"]
    assert next_seq == 10


@pytest.mark.parametrize(
    "response",
    ["<div>缺少表格</div>", _personnel([("A", "B", "C", "D", "E")], total=2)],
)
def test_maintenance_personnel_rejects_missing_or_incomplete_table(response: str) -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    with pytest.raises(MMISClientError):
        reader._read_maintenance_personnel(response, state=STATE, xhr_seq=9)


def test_basic_information_rejects_mismatch_and_conflicting_duplicate() -> None:
    with pytest.raises(MMISClientError, match="工作單與輸入不相符"):
        parse_daily_inspection_basic_info(_basic_info(), expected_work_order="115-1A-99999")
    conflicting = (
        _basic_info()
        + '<label for="duplicate">車次:</label><input id="duplicate" value="9">'
    )
    with pytest.raises(MMISClientError, match="車次.*不一致"):
        parse_daily_inspection_basic_info(conflicting, expected_work_order="115-1A-71815")


def test_basic_information_formats_date_and_datetime_from_dojo_value() -> None:
    html = _basic_info()
    html = html.replace(
        'id="basic-2" value="2026/10/06"',
        'id="basic-2" value="" dojovalue="1791216000000"',
    )
    html = html.replace(
        'id="basic-6" value="2026/09/26 01:15"',
        'id="basic-6" value="" dojovalue="1790356547154"',
    )
    assert parse_daily_inspection_basic_info(
        html, expected_work_order="115-1A-71815"
    ) == BASIC_VALUES


def test_tool_rejects_wrong_arg_count_before_loading_config() -> None:
    with pytest.raises(MMISClientError, match="用法"):
        tool.execute([])


def test_groups_maintenance_personnel_by_group_and_role_sorted_by_name() -> None:
    rows = [
        {"人員群組": group, "工作角色": role, "員工代號": code,
         "姓名": name, "單位": "新竹機務段"}
        for group, role, code, name in [
            ("檢查室", "檢查員", "E2", "乙"),
            ("檢車室", "修繕人員", "E5", "戊"),
            ("檢查室", "修繕人員", "E3", "丙"),
            ("檢車室", "檢查員", "E4", "丁"),
            ("檢查室", "檢查員", "E1", "甲"),
            ("檢車室", "修繕人員", "E6", "己"),
            ("其他", "檢查員", "E7", "庚"),
        ]
    ]
    original = {"count": 7, "records": rows}
    result = tool.group_maintenance_personnel(original)
    assert list(result) == [
        "檢查室（檢查員）", "檢查室（技術人員）",
        "檢車室（檢查員）", "檢車室（技術人員）",
    ]
    assert original == {"count": 7, "records": rows}
    assert result["檢查室（檢查員）"] == {
        "count": 2,
        "records": [{"員工代號": "E2", "姓名": "乙"}, {"員工代號": "E1", "姓名": "甲"}],
    }
    assert result["檢查室（技術人員）"] == {
        "count": 1, "records": [{"員工代號": "E3", "姓名": "丙"}],
    }
    assert result["檢車室（檢查員）"] == {
        "count": 1, "records": [{"員工代號": "E4", "姓名": "丁"}],
    }
    assert result["檢車室（技術人員）"] == {
        "count": 2,
        "records": [{"員工代號": "E6", "姓名": "己"}, {"員工代號": "E5", "姓名": "戊"}],
    }


def test_groups_maintenance_personnel_with_no_matching_rows() -> None:
    result = tool.group_maintenance_personnel({"count": 0, "records": []})
    assert list(result) == [title for title, _, _ in tool.PERSONNEL_GROUPS]
    assert all(result[title] == {"count": 0, "records": []}
               for title, _, _ in tool.PERSONNEL_GROUPS)


def test_tool_nests_only_count_and_records_under_inspection_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        **BASIC_VALUES,
        "success": True,
        "query_name": "查詢日檢工單檢修記錄",
        "work_order": "115-1A-71815",
        "count": 1,
        "records": [
            {"裝置名稱": "列車自動防護系統", "回報結果": "異常", "備註": "排修"}
        ],
        "important_notes": {"count": 0, "records": []},
        "linked_fault_notices": {"count": 1, "records": [{"故障通報號": "1151006-32"}]},
        "maintenance_personnel": {"count": 0, "records": []},
    }
    monkeypatch.setattr(tool, "MMISConfig", SimpleNamespace(from_env=lambda: object()))
    monkeypatch.setattr(tool, "MMISSession", lambda config: object())
    monkeypatch.setattr(
        tool,
        "DailyInspectionInspectionRecordReader",
        lambda client: SimpleNamespace(run=lambda number: payload),
    )

    output = tool.execute(["115-1A-71815"])
    assert output == {
        "query_name": "查詢日檢工單檢修記錄",
        "query_work_order_number": "115-1A-71815",
        "success": True,
        **BASIC_VALUES,
        "已勾稽故障通報": payload["linked_fault_notices"],
        "檢修記錄": {"count": 1, "records": payload["records"]},
        "重要事項紀錄": {"count": 0, "records": []},
        "檢修人員": {
            **{
                title: {"count": 0, "records": []}
                for title, _, _ in tool.PERSONNEL_GROUPS
            },
        },
    }
    assert list(output) == [
        "query_name", "query_work_order_number", "success", *BASIC_VALUES,
        "已勾稽故障通報", "檢修記錄", "重要事項紀錄", "檢修人員",
    ]
