from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.daily_inspection.not_submitted import (
    DailyInspectionNotSubmittedQuery,
    FIELDS,
)
from mmis_connector.parser import parse_maximo_table


STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-11-02_query-daily-inspection-work-orders-not-submitted-for-approval"
    r"\dom\2026-11-02T071923-275.html"
)


def _page(
    start: int, end: int, total: int, *, next_page: bool,
    work_order_offset: int = 0, depot: str = "新竹機務段",
) -> str:
    headers = "".join(
        f'<span id="table_ttrow_[C:{i}]_ttitle-lb">{field}</span>'
        for i, field in enumerate((*FIELDS[:-1], "逾期標註?"), start=1)
    )

    def row_html(number: int) -> str:
        values = {
            1: depot,
            5: str(number + work_order_offset),
            8: "執行中已派工",
            11: "2026/11/01",
        }
        cells = "".join(
            f'<td id="table_tdrow_[C:{column}]-c[R:{number - start}]">'
            f'<span> {values.get(column, field)} </span></td>'
            for column, field in enumerate((*FIELDS[:-1], "逾期標註?"), start=1)
        )
        return f'<tr id="table_tbod_tdrow-tr[R:{number - start}]">{cells}</tr>'

    rows = "".join(
        row_html(number)
        for number in range(start, end + 1)
    )
    next_control = (
        '<a id="table-ti7"><img id="table-ti7_img" src="tablebtn_next_on.gif"></a>'
        if next_page else ""
    )
    return (
        headers + f'<label id="table-lb3" class="tCount">{start} - {end}/{total}</label>'
        + next_control + rows
    )


def _query(monkeypatch: pytest.MonkeyPatch, pages: list[str]):
    query = DailyInspectionNotSubmittedQuery(SimpleNamespace(state=STATE))
    monkeypatch.setattr(query, "open_all_records", lambda: (STATE, SimpleNamespace(prefix="table")))
    calls: list[dict[str, Any]] = []
    responses = iter(["", "", "", *pages])

    def fake_post_event(**kwargs: Any) -> str:
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(query, "_post_event", fake_post_event)
    return query, calls


def test_reads_all_31_records_and_uses_current_date(monkeypatch: pytest.MonkeyPatch) -> None:
    query, calls = _query(
        monkeypatch,
        [_page(1, 30, 31, next_page=True), _page(31, 31, 31, next_page=False)],
    )
    result = query.run(today=datetime(2026, 11, 2))

    assert result["count"] == 31
    assert [row["工作單"] for row in result["records"]] == [str(i) for i in range(1, 32)]
    assert list(result["records"][0]) == list(FIELDS)
    assert result["records"][0]["逾期標註"] is False
    assert [(call["event_type"], call["value"]) for call in calls[:4]] == [
        ("setvalue", "新竹機務段"),
        ("setvalue", "<2026/11/02"),
        ("setvalue", "執行中已派工"),
        ("filterrows", ""),
    ]
    assert calls[-1]["target_id"] == "table-ti7"
    assert calls[-1]["xhr_seq"] == 7


def test_rejects_missing_next_page(monkeypatch: pytest.MonkeyPatch) -> None:
    query, _ = _query(monkeypatch, [_page(1, 30, 31, next_page=False)])
    with pytest.raises(MMISClientError, match="找不到下一頁"):
        query.run(today=datetime(2026, 11, 2))


def test_rejects_duplicate_work_order_across_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    query, _ = _query(
        monkeypatch,
        [_page(1, 1, 2, next_page=True), _page(2, 2, 2, next_page=False, work_order_offset=-1)],
    )
    with pytest.raises(MMISClientError, match="重複工作單"):
        query.run(today=datetime(2026, 11, 2))


def test_rejects_stale_filter_result(monkeypatch: pytest.MonkeyPatch) -> None:
    query, _ = _query(monkeypatch, [_page(1, 1, 1, next_page=False, depot="其他機務段")])
    with pytest.raises(MMISClientError, match="不符合查詢條件"):
        query.run(today=datetime(2026, 11, 2))


@pytest.mark.skipif(not RECORDED_DOM.exists(), reason="本機未提供錄製 DOM")
def test_recorded_page_has_all_requested_fields() -> None:
    schema, rows = parse_maximo_table(
        RECORDED_DOM.read_text(encoding="utf-8"),
        required_headers=set(FIELDS[:-1]) | {"逾期標註?"},
        checkbox_headers={"逾期標註?"},
    )
    assert schema is not None
    assert len(rows) == 1
    assert rows[0]["工作單"] == "115-1A-80870"
    assert rows[0]["逾期標註?"] is False


@pytest.mark.skipif(not RECORDED_DOM.exists(), reason="本機未提供錄製 DOM")
def test_query_returns_recorded_work_order(monkeypatch: pytest.MonkeyPatch) -> None:
    query, _ = _query(monkeypatch, [RECORDED_DOM.read_text(encoding="utf-8")])
    result = query.run(today=datetime(2026, 11, 2))

    assert result["count"] == 1
    assert result["records"][0]["工作單"] == "115-1A-80870"
    assert result["records"][0]["階段核簽人"] == ""
