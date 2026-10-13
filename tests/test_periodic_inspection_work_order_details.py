from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.parser import parse_maximo_table
from mmis_connector.periodic_inspection.reader import (
    PeriodicInspectionWorkOrderDetailReader,
)
from tools.mmis_development import query_periodic_inspection_work_order_details as tool


RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-13_query-periodic-inspection-work-order-details"
    r"\dom\2026-10-13T055217-284.html"
)
STATE = PageState("session", 2, "csrf", "zz_pmwo", "https://example.test/app")


def _list_result(number: str) -> str:
    return (
        '<label id="list-lb3" class="tCount">1 - 1/1</label>'
        '<table id="list_tbod-tbd" summary="工作單">'
        '<span id="list_ttrow_[C:5]_ttitle-lb">工作單</span>'
        '<tr id="list_tbod_tdrow-tr[R:0]">'
        f'<td id="list_tdrow_[C:5]-c[R:0]"><span title="{number}">{number}</span></td>'
        '</tr></table>'
    )


def _record_page(
    remarks: list[str], *, start: int, total: int, next_page: bool = False
) -> str:
    headers = "".join(
        f'<span id="work_ttrow_[C:{index}]_ttitle-lb">{field}</span>'
        for index, field in (
            (3, "裝置名稱"), (4, "檢修項目"), (6, "回報結果"), (8, "備註")
        )
    )
    rows = "".join(
        f'<tr id="work_tbod_tdrow-tr[R:{index}]">'
        f'<td id="work_tdrow_[C:3]-c[R:{index}]"><span title="裝置{start + index}"></span></td>'
        f'<td id="work_tdrow_[C:4]-c[R:{index}]"><span title="項目{start + index}"></span></td>'
        f'<td id="work_tdrow_[C:6]-c[R:{index}]"><span title="良好"></span></td>'
        f'<td id="work_tdrow_[C:8]-c[R:{index}]">'
        f'<input id="work_tdrow_[C:8]_txt-tb[R:{index}]" value="{remark}"></td>'
        '</tr>'
        for index, remark in enumerate(remarks)
    )
    count = f"{start} - {start + len(remarks) - 1}/{total}" if total else "0 - 0/0"
    next_button = (
        '<a id="work-ti7"><img id="work-ti7_img" src="tablebtn_next_on.gif"></a>'
        if next_page else ""
    )
    return (
        f'<label id="work-lb3" class="tCount">{count}</label>{next_button}'
        f'<table id="work_tbod-tbd" summary="工作單的作業 123">{headers}{rows}</table>'
    )


def _run_pages(pages: list[str]) -> tuple[dict, list[tuple[str, str]]]:
    number = "115-2A-69254-001"
    reader = PeriodicInspectionWorkOrderDetailReader(SimpleNamespace(state=STATE))
    calls: list[tuple[str, str]] = []

    class FakeEvents:
        def load_app_with_response(self, **kwargs):
            assert kwargs["app_value"] == "ZZ_PMWO"
            return STATE, _list_result(number)

        def post(self, **kwargs):
            calls.append((kwargs["event_type"], kwargs["target_id"]))
            sequence = len(calls)
            if sequence == 1:
                return '<div id="mainrec_menus"></div>'
            if sequence == 2:
                return _list_result(number)
            if sequence == 3:
                assert kwargs["value"] == number
                return ""
            if sequence == 4:
                return _list_result(number)
            if sequence == 5:
                return (
                    '<label for="order-tb">工作單:</label>'
                    f'<input id="order-tb" value="{number}">'
                    '<li id="report-tab" ctype="tab">'
                    '<a title="檢修回報"></a></li>'
                )
            if sequence == 6:
                return '<li id="record-tab" ctype="tab"><a title="檢修記錄"></a></li>'
            return pages[sequence - 7]

    reader.events = FakeEvents()
    return reader.run(number), calls


def test_reads_only_nonblank_remarks_across_pages() -> None:
    result, calls = _run_pages([
        _record_page(["  ", "需處理"], start=1, total=3, next_page=True),
        _record_page(["再次檢查"], start=3, total=3),
    ])
    assert result["檢修記錄"] == {
        "count": 2,
        "records": [
            {"裝置名稱": "裝置2", "檢修項目": "項目2", "回報結果": "良好", "備註": "需處理"},
            {"裝置名稱": "裝置3", "檢修項目": "項目3", "回報結果": "良好", "備註": "再次檢查"},
        ],
    }
    assert calls[-1] == ("click", "work-ti7")


def test_all_blank_remarks_return_empty_records() -> None:
    result, _ = _run_pages([_record_page(["", "  "], start=1, total=2)])
    assert result["檢修記錄"] == {"count": 0, "records": []}


def test_missing_next_page_fails_instead_of_returning_partial_results() -> None:
    with pytest.raises(MMISClientError, match="找不到下一頁"):
        _run_pages([_record_page(["備註"], start=1, total=2)])


@pytest.mark.skipif(not RECORDED_DOM.exists(), reason="本機未提供定期檢修錄製 DOM")
def test_recorded_dom_has_one_nonblank_remark_and_four_fields() -> None:
    html = RECORDED_DOM.read_text(encoding="utf-8")
    _, rows = parse_maximo_table(
        html, required_headers={"裝置名稱", "檢修項目", "回報結果", "備註"}
    )
    matching = [row for row in rows if str(row["備註"]).strip()]
    assert len(rows) == 58
    assert len(matching) == 1
    assert all(matching[0][field] for field in ("裝置名稱", "檢修項目", "回報結果", "備註"))


def test_tool_rejects_wrong_arg_count_before_loading_config(monkeypatch, capsys) -> None:
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: pytest.fail("unexpected config load"))
    assert tool.main([]) == 1
    error = json.loads(capsys.readouterr().out)
    assert error["error"] == "MMISClientError"


def test_invalid_work_order_fails_before_app_load() -> None:
    reader = PeriodicInspectionWorkOrderDetailReader(SimpleNamespace(state=None))
    with pytest.raises(MMISClientError, match="工作單號"):
        reader.run("115/2A/69254")
