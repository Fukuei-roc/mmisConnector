from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.parser import MaximoTableSchema, parse_maximo_table
from mmis_connector.query_daily_inspection_work_orders_by_vehicle_and_date import (
    REQUIRED_HEADERS,
)
from mmis_connector.read_daily_inspection_work_order import (
    FAULT_HEADERS,
    FAULT_TABLE_SUMMARY,
    DailyInspectionWorkOrderDetailReader,
    normalize_work_order,
)


STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
LIST_SCHEMA = MaximoTableSchema(
    "daily",
    {
        1: "檢修段",
        3: "車組/車號",
        5: "工作單",
        8: "工作單狀態",
        11: "檢修日期",
    },
)
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-09-23_query-daily-inspection-work-order-by-number\dom"
    r"\2026-09-23T065147-029.html"
)


def _daily_results(work_orders: list[str]) -> str:
    headers = "".join(
        f'<span id="daily_ttrow_[C:{column}]_ttitle-lb">{label}</span>'
        for column, label in LIST_SCHEMA.headers.items()
    )
    if not work_orders:
        return headers + "<message>沒有要顯示的列。</message>"
    rows = []
    for row_number, work_order in enumerate(work_orders):
        cells = "".join(
            f'<td id="daily_tdrow_[C:{column}]-c[R:{row_number}]">'
            f'<span id="daily_{column}_ttxt-lb[R:{row_number}]" '
            f'title="{value}">{value}</span></td>'
            for column, value in {
                1: "新竹機務段",
                3: "EMU933",
                5: work_order,
                11: "2026/09/23",
            }.items()
        )
        rows.append(
            f'<tr id="daily_tbod_tdrow-tr[R:{row_number}]">{cells}</tr>'
        )
    return (
        headers
        + f'<label id="daily-lb3" class="tCount">1 - {len(rows)}/{len(rows)}</label>'
        + "".join(rows)
    )


def _fault_table(*, include_row: bool = True, total: int = 1) -> str:
    headers = {
        0: "故障通報號",
        1: "發生日期",
        2: "車組/車號",
        3: "故障現象",
    }
    header_html = "".join(
        f'<span id="fault_ttrow_[C:{column}]_ttitle-lb">{label}</span>'
        for column, label in headers.items()
    )
    row_html = ""
    if include_row:
        values = {
            0: "1150916-17",
            1: "2026/09/16",
            2: "EMU933",
            3: "第一行<br/>第二行",
        }
        cells = "".join(
            f'<td id="fault_tdrow_[C:{column}]-c[R:0]">'
            f'<span title="{value}">{value}</span></td>'
            for column, value in values.items()
        )
        row_html = f'<tr id="fault_tbod_tdrow-tr[R:0]">{cells}</tr>'
    count = (
        f'<label id="fault-lb3" class="tCount">1 - 1/{total}</label>'
        if include_row
        else ""
    )
    next_control = (
        '<a id="fault-ti7"><img id="fault-ti7_img" '
        'src="tablebtn_next_on.gif" /></a>'
        if total > 1
        else ""
    )
    return (
        f'<section>{count}{next_control}<table summary="{FAULT_TABLE_SUMMARY}">'
        f"{header_html}{row_html}</table></section>"
    )


def _run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    work_orders: list[str] | None = None,
    detail_response: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    client = SimpleNamespace(state=STATE)
    reader = DailyInspectionWorkOrderDetailReader(client)
    monkeypatch.setattr(
        reader.list_query,
        "open_all_records",
        lambda: (STATE, LIST_SCHEMA),
    )
    responses = iter(
        [
            "",
            _daily_results(
                ["115-1A-70048"] if work_orders is None else work_orders
            ),
            detail_response or _fault_table(),
        ]
    )
    calls: list[dict[str, Any]] = []

    def fake_post_event(**kwargs: Any) -> str:
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader, "_post_event", fake_post_event)
    return reader.run(" 115-1A-70048 "), calls


@pytest.mark.parametrize(
    "value", ["", "   ", "-", "115/1A/70048", "工單-1", "A B"]
)
def test_rejects_invalid_work_order_before_network(value: str) -> None:
    with pytest.raises(MMISClientError, match="工作單號"):
        normalize_work_order(value)


def test_normalizes_valid_work_order() -> None:
    assert normalize_work_order(" 115-1A-70048 ") == "115-1A-70048"


def test_run_filters_exact_work_order_and_clicks_unique_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run(monkeypatch)

    assert [(call["event_type"], call["value"]) for call in calls] == [
        ("setvalue", "115-1A-70048"),
        ("filterrows", ""),
        ("click", ""),
    ]
    assert calls[0]["target_id"] == "daily_tfrow_[C:5]_txt-tb"
    assert calls[1]["target_id"] == "daily_tbod_tfrow-tr"
    assert calls[2]["target_id"] == "daily_tdrow_[C:5]_ttxt-lb[R:0]"
    assert result["has_fault_notices"] is True
    assert result["count"] == 1
    assert result["records"][0]["故障現象"] == "第一行\n第二行"


def test_run_returns_explicit_empty_fault_notice_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run(monkeypatch, detail_response=_fault_table(include_row=False))

    assert result["has_fault_notices"] is False
    assert result["count"] == 0
    assert result["records"] == []


def test_run_rejects_missing_work_order(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="找不到工作單"):
        _run(monkeypatch, work_orders=[])


def test_run_rejects_multiple_work_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="不是唯一一筆"):
        _run(monkeypatch, work_orders=["115-1A-70048", "115-1A-70048"])


def test_run_rejects_non_exact_work_order(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="不相符"):
        _run(monkeypatch, work_orders=["115-1A-99999"])


def test_run_rejects_missing_fault_table(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="故障通報管理"):
        _run(monkeypatch, detail_response="<div>工單明細但缺少目標表格</div>")


def test_run_rejects_incomplete_fault_notice_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(MMISClientError, match="不完整資料"):
        _run(monkeypatch, detail_response=_fault_table(total=2))


@pytest.mark.skipif(
    not RECORDED_DOM.exists(),
    reason="本機未提供工作單明細錄製 DOM",
)
def test_parse_recorded_detail_extracts_six_fault_notices() -> None:
    _, rows = parse_maximo_table(
        RECORDED_DOM.read_text(encoding="utf-8"),
        required_headers=FAULT_HEADERS,
        table_summary=FAULT_TABLE_SUMMARY,
        normalize_line_breaks=True,
    )

    assert len(rows) == 6
    assert set(rows[0]) == FAULT_HEADERS
    assert [row["故障通報號"] for row in rows] == [
        "1150916-17",
        "1150916-59",
        "1150917-23",
        "1150917-51",
        "1150918-02",
        "1150918-03",
    ]
    assert rows[0]["故障現象"] == (
        "EM9334代碼:241故障,牽引MOCK1~4有接觸器未閉合\n"
        "ED9332端MMI時速表刻度0~10位置有尖銳物割狠"
    )
    assert "\n" in rows[1]["故障現象"]
    assert "<br" not in rows[1]["故障現象"]


def test_named_table_parser_does_not_accept_unrelated_headers() -> None:
    response = (
        '<table summary="其他表格">'
        '<span id="other_ttrow_[C:0]_ttitle-lb">故障通報號</span>'
        '<span id="other_ttrow_[C:1]_ttitle-lb">發生日期</span>'
        '<span id="other_ttrow_[C:2]_ttitle-lb">車組/車號</span>'
        '<span id="other_ttrow_[C:3]_ttitle-lb">故障現象</span>'
        "</table>"
    )
    with pytest.raises(MMISClientError, match="故障通報管理"):
        parse_maximo_table(
            response,
            required_headers=FAULT_HEADERS,
            table_summary=FAULT_TABLE_SUMMARY,
        )


def test_line_break_normalization_is_opt_in() -> None:
    _, rows = parse_maximo_table(
        _fault_table(),
        required_headers=FAULT_HEADERS,
        table_summary=FAULT_TABLE_SUMMARY,
    )
    assert rows[0]["故障現象"] == "第一行<br/>第二行"


def test_daily_result_fixture_matches_required_headers() -> None:
    _, rows = parse_maximo_table(
        _daily_results(["115-1A-70048"]), required_headers=REQUIRED_HEADERS
    )
    assert rows[0]["工作單"] == "115-1A-70048"
