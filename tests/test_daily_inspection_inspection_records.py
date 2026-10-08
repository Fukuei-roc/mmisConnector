from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.daily_inspection.reader import DailyInspectionInspectionRecordReader
from tools.mmis_development import query_daily_inspection_work_order_inspection_records as tool


STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-07_query-daily-inspection-work-order-details\dom"
    r"\2026-10-07T065114-823.html"
)


def _tab(title: str, target: str) -> str:
    return f'<li ctype="tab" id="{target}"><a title="{title}">{title}</a></li>'


NOTE_FIELDS = (
    "車組/車號", "故障類別", "故障類別說明", "故障現象", "故障原因",
    "處置措施", "材料編號(PA)", "員工代號", "人員姓名",
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


def _run(monkeypatch: pytest.MonkeyPatch, response: str) -> tuple[dict[str, Any], list[str]]:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    monkeypatch.setattr(
        reader,
        "open_detail",
        lambda number: ("115-1A-71815", _tab("檢修回報", "report-tab")),
    )
    calls: list[str] = []

    def post_event(**kwargs: Any) -> str:
        calls.append(kwargs["target_id"])
        return (_tab("檢修記錄", "records-tab") + _notes([])) if len(calls) == 1 else response

    monkeypatch.setattr(reader, "_post_event", post_event)
    return reader.run("115-1A-71815"), calls


def test_reads_only_nonempty_remarks_and_uses_both_tabs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run(monkeypatch, _table(["", " 洩漏 ", "  ", "停用"]))
    assert calls == ["report-tab", "records-tab"]
    assert result["count"] == 2
    assert result["records"] == [
        {"裝置名稱": "裝置1", "回報結果": "異常", "備註": "洩漏"},
        {"裝置名稱": "裝置3", "回報結果": "異常", "備註": "停用"},
    ]
    assert result["important_notes"] == {"count": 0, "records": []}


def test_all_empty_remarks_are_successful_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run(monkeypatch, _table(["", "  "]))
    assert result["success"] is True
    assert result["count"] == 0
    assert result["records"] == []


def test_reads_all_pages_without_losing_order(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = DailyInspectionInspectionRecordReader(SimpleNamespace(state=STATE))
    monkeypatch.setattr(
        reader,
        "open_detail",
        lambda number: ("115-1A-71815", _tab("檢修回報", "report-tab")),
    )
    responses = iter(
        [
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
    assert targets == ["report-tab", "records-tab", "work-ti7"]
    assert [record["備註"] for record in result["records"]] == ["第一頁", "第二頁"]


def test_empty_source_table_is_successful(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _run(monkeypatch, _table([]))
    assert result["count"] == 0
    assert result["records"] == []


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


def test_tool_rejects_wrong_arg_count_before_loading_config() -> None:
    with pytest.raises(MMISClientError, match="用法"):
        tool.execute([])


def test_tool_nests_only_count_and_records_under_inspection_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "success": True,
        "query_name": "查詢日檢工單檢修記錄",
        "work_order": "115-1A-10899",
        "count": 1,
        "records": [
            {"裝置名稱": "列車自動防護系統", "回報結果": "異常", "備註": "排修"}
        ],
        "important_notes": {"count": 0, "records": []},
    }
    monkeypatch.setattr(tool, "MMISConfig", SimpleNamespace(from_env=lambda: object()))
    monkeypatch.setattr(tool, "MMISSession", lambda config: object())
    monkeypatch.setattr(
        tool,
        "DailyInspectionInspectionRecordReader",
        lambda client: SimpleNamespace(run=lambda number: payload),
    )

    assert tool.execute(["115-1A-10899"]) == {
        "success": True,
        "query_name": "查詢日檢工單檢修記錄",
        "work_order": "115-1A-10899",
        "檢修記錄": {"count": 1, "records": payload["records"]},
        "重要事項紀錄": {"count": 0, "records": []},
    }
