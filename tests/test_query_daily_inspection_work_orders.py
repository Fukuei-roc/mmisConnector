from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.parser import parse_maximo_table
from mmis_connector.query_daily_inspection_work_orders import (
    DEPOT,
    REQUIRED_HEADERS,
    DailyInspectionWorkOrderQuery,
    normalize_inspection_date,
    normalize_vehicle,
)


STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-09-23_query-daily-inspection-work-orders\dom"
    r"\2026-09-23T054325-594.html"
)


def _table(*, no_rows: bool = False, total: int = 1) -> str:
    headers = {
        1: "檢修段",
        3: "車組/車號",
        5: "工作單",
        11: "檢修日期",
    }
    header_html = "".join(
        f'<span id="table_ttrow_[C:{column}]_ttitle-lb">{label}</span>'
        for column, label in headers.items()
    )
    if no_rows:
        return header_html + "<message>沒有要顯示的列。</message>"
    row = "".join(
        f'''<td id="table_tdrow_[C:{column}]-c[R:0]">
          <span id="table_value_{column}_ttxt-lb[R:0]">{value}</span>
        </td>'''
        for column, value in {
            1: DEPOT,
            3: "EMU703",
            5: "115-1A-70877",
            11: "2026/09/23",
        }.items()
    )
    return f'''{header_html}
      <label id="table-lb3" class="tCount">1 - 1/{total}</label>
      <tr id="table_tbod_tdrow-tr[R:0]">{row}</tr>'''


def _run(monkeypatch: pytest.MonkeyPatch, result_page: str):
    client = SimpleNamespace(state=STATE)
    query = DailyInspectionWorkOrderQuery(client)
    calls: list[dict[str, Any]] = []
    responses = iter(["<div>mainrec_menus</div>", _table(), "", "", "", result_page])
    monkeypatch.setattr(query, "_load_app", lambda: STATE)

    def fake_post_event(**kwargs: Any) -> str:
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(query, "_post_event", fake_post_event)
    return query.run(" 703 ", "2026/9/22"), calls


def test_normalizes_inputs_before_network_use() -> None:
    assert normalize_vehicle(" 703 ") == "703"
    assert normalize_inspection_date("2026/9/2") == "2026/09/02"
    assert normalize_inspection_date(">2026/09/22") == "2026/09/22"


@pytest.mark.parametrize("value", ["", "2026-09-22", "2026/02/30", ">>2026/09/22"])
def test_rejects_invalid_inspection_date(value: str) -> None:
    with pytest.raises(MMISClientError, match="檢修日期"):
        normalize_inspection_date(value)


def test_rejects_blank_vehicle() -> None:
    with pytest.raises(MMISClientError, match="車組/車號"):
        normalize_vehicle("   ")


def test_run_replays_recorded_filter_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    result, calls = _run(monkeypatch, _table())

    assert result["count"] == 1
    assert result["records"][0]["工作單"] == "115-1A-70877"
    assert [(call["event_type"], call["value"]) for call in calls] == [
        ("click", ""),
        ("click", "useAllRecsQuery_OPTION"),
        ("setvalue", DEPOT),
        ("setvalue", "703"),
        ("setvalue", ">2026/09/22"),
        ("filterrows", ""),
    ]
    assert calls[-1]["target_id"] == "table_tbod_tfrow-tr"


def test_run_reports_valid_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _run(monkeypatch, _table(no_rows=True))

    assert result["count"] == 0
    assert result["records"] == []
    assert result["message"] == "找不到對應工單"


def test_run_rejects_result_larger_than_one_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(MMISClientError, match="不完整資料"):
        _run(monkeypatch, _table(total=2))


@pytest.mark.skipif(
    not RECORDED_DOM.exists(),
    reason="本機未提供日檢工單錄製 DOM",
)
def test_parse_recorded_daily_inspection_dom() -> None:
    _, rows = parse_maximo_table(
        RECORDED_DOM.read_text(encoding="utf-8"),
        required_headers=REQUIRED_HEADERS,
        checkbox_headers={"逾期標註?"},
    )

    assert len(rows) == 1
    assert rows[0]["車組/車號"] == "EMU703"
    assert rows[0]["工作單"].startswith("115-1A-")
    assert rows[0]["檢修日期"] == "2026/09/23"
