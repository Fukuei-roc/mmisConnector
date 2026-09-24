from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.link_fault_notice_to_daily_inspection_work_order_by_number import (
    OPERATION_NAME,
    DailyInspectionWorkOrderFaultNoticeLinker,
    normalize_fault_notice,
)
from mmis_connector.parser import (
    parse_fault_notice_link_controls,
    parse_maximo_table,
    parse_maximo_table_schema,
)
from mmis_connector.query_daily_inspection_work_orders_by_vehicle_and_date import (
    REQUIRED_HEADERS,
)
from mmis_connector.query_fault_notices_linked_to_daily_inspection_work_order_by_number import (
    FAULT_HEADERS,
    FAULT_TABLE_SUMMARY,
)


STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
RECORDING_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-09-24_query-daily-inspection-work-order-by-number-and-cross-check-fault-reports"
    r"\dom"
)
RECORDED_LINKED_DETAIL = RECORDING_DOM / "2026-09-24T062105-558.html"
RECORDED_RETURNED_LIST = RECORDING_DOM / "2026-09-24T062118-355.html"


def _detail_controls(*, duplicate_button: bool = False) -> str:
    extra_button = (
        '<button id="other-link">勾稽指定故障通報號</button>'
        if duplicate_button
        else ""
    )
    return (
        '<label id="fault-label" for="fault-input">故障通報號:</label>'
        '<input id="fault-input" aria-labelledby="fault-label" />'
        '<button id="link-button">勾稽指定故障通報號</button>'
        f"{extra_button}"
        '<li id="list-tab" ctype="tab">'
        '<a id="list-anchor" title="清單">清單</a></li>'
    )


def _fault_table(fault_notice: str) -> str:
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
    values = {
        0: fault_notice,
        1: "2026/09/23",
        2: "EMU710",
        3: "測試故障",
    }
    cells = "".join(
        f'<td id="fault_tdrow_[C:{column}]-c[R:0]">'
        f'<span title="{value}">{value}</span></td>'
        for column, value in values.items()
    )
    return (
        '<table summary="故障通報管理">'
        f"{header_html}"
        f'<tr id="fault_tbod_tdrow-tr[R:0]">{cells}</tr>'
        "</table>"
    )


def _daily_list() -> str:
    headers = {
        1: "檢修段",
        3: "車組/車號",
        5: "工作單",
        8: "工作單狀態",
        11: "檢修日期",
    }
    return "".join(
        f'<span id="daily_ttrow_[C:{column}]_ttitle-lb">{label}</span>'
        for column, label in headers.items()
    )


def _linker(monkeypatch: pytest.MonkeyPatch) -> DailyInspectionWorkOrderFaultNoticeLinker:
    client = SimpleNamespace(state=STATE)
    linker = DailyInspectionWorkOrderFaultNoticeLinker(client)
    monkeypatch.setattr(
        linker.detail_reader,
        "open_detail",
        lambda work_order: (work_order.strip(), _detail_controls()),
    )
    return linker


@pytest.mark.parametrize(
    "value", ["", " ", "-1150923", "故障-1", "1150923/36", "A" * 21]
)
def test_rejects_invalid_fault_notice_before_network(value: str) -> None:
    with pytest.raises(MMISClientError, match="故障通報號"):
        normalize_fault_notice(value)


def test_normalizes_valid_fault_notice() -> None:
    assert normalize_fault_notice(" 1150923-36 ") == "1150923-36"


def test_parses_dynamic_link_controls() -> None:
    controls = parse_fault_notice_link_controls(_detail_controls())

    assert controls.input_target == "fault-input"
    assert controls.button_target == "link-button"
    assert controls.list_target == "list-tab"


def test_rejects_ambiguous_link_controls() -> None:
    with pytest.raises(MMISClientError, match="唯一"):
        parse_fault_notice_link_controls(_detail_controls(duplicate_button=True))


def test_rejects_label_that_does_not_target_an_input() -> None:
    invalid = _detail_controls().replace(
        '<input id="fault-input" aria-labelledby="fault-label" />',
        '<div id="fault-input"></div>',
    )

    with pytest.raises(MMISClientError, match="輸入框"):
        parse_fault_notice_link_controls(invalid)


def test_run_links_with_one_multi_event_post_and_returns_to_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linker = _linker(monkeypatch)
    multi_calls: list[dict[str, Any]] = []
    single_calls: list[dict[str, Any]] = []

    def post_events(**kwargs: Any) -> str:
        multi_calls.append(kwargs)
        return _fault_table("1150923-36")

    def post(**kwargs: Any) -> str:
        single_calls.append(kwargs)
        return _daily_list()

    monkeypatch.setattr(linker.events, "post_events", post_events)
    monkeypatch.setattr(linker.events, "post", post)

    result = linker.run(" 115-1A-71002 ", " 1150923-36 ")

    assert multi_calls[0]["events"] == [
        ("setvalue", "fault-input", "1150923-36"),
        ("click", "link-button", ""),
    ]
    assert multi_calls[0]["xhr_seq"] == 6
    assert single_calls[0]["target_id"] == "list-tab"
    assert single_calls[0]["xhr_seq"] == 7
    assert result == {
        "success": True,
        "operation_name": OPERATION_NAME,
        "work_order": "115-1A-71002",
        "fault_notice": "1150923-36",
        "linked": True,
        "returned_to_list": True,
    }


def test_run_still_sends_link_when_notice_is_already_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linker = _linker(monkeypatch)
    monkeypatch.setattr(
        linker.detail_reader,
        "open_detail",
        lambda work_order: (
            work_order,
            _detail_controls() + _fault_table("1150923-36"),
        ),
    )
    calls = []
    monkeypatch.setattr(
        linker.events,
        "post_events",
        lambda **kwargs: calls.append(kwargs) or _fault_table("1150923-36"),
    )
    monkeypatch.setattr(linker.events, "post", lambda **kwargs: _daily_list())

    linker.run("115-1A-71002", "1150923-36")

    assert len(calls) == 1


def test_run_reports_unknown_result_when_write_request_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linker = _linker(monkeypatch)

    def fail(**kwargs: Any) -> str:
        raise MMISClientError("network")

    monkeypatch.setattr(linker.events, "post_events", fail)

    with pytest.raises(MMISClientError, match="結果不明"):
        linker.run("115-1A-71002", "1150923-36")


def test_run_rejects_unconfirmed_link_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linker = _linker(monkeypatch)
    monkeypatch.setattr(
        linker.events,
        "post_events",
        lambda **kwargs: _fault_table("1150923-99"),
    )

    with pytest.raises(MMISClientError, match="無法確認"):
        linker.run("115-1A-71002", "1150923-36")


def test_run_distinguishes_return_to_list_failure_after_confirmed_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linker = _linker(monkeypatch)
    monkeypatch.setattr(
        linker.events,
        "post_events",
        lambda **kwargs: _fault_table("1150923-36"),
    )
    monkeypatch.setattr(linker.events, "post", lambda **kwargs: "not a list")

    with pytest.raises(MMISClientError, match="勾稽已確認，但返回清單失敗"):
        linker.run("115-1A-71002", "1150923-36")


@pytest.mark.skipif(
    not RECORDED_LINKED_DETAIL.exists() or not RECORDED_RETURNED_LIST.exists(),
    reason="本機未提供勾稽流程錄製 DOM",
)
def test_recorded_dom_contains_link_controls_confirmation_and_returned_list() -> None:
    detail_html = RECORDED_LINKED_DETAIL.read_text(encoding="utf-8")
    list_html = RECORDED_RETURNED_LIST.read_text(encoding="utf-8")

    controls = parse_fault_notice_link_controls(detail_html)
    _, fault_notices = parse_maximo_table(
        detail_html,
        required_headers=FAULT_HEADERS,
        table_summary=FAULT_TABLE_SUMMARY,
        normalize_line_breaks=True,
    )
    list_schema = parse_maximo_table_schema(
        list_html,
        required_headers=REQUIRED_HEADERS,
    )

    assert controls.input_target
    assert controls.button_target
    assert controls.list_target
    assert any(row["故障通報號"] == "1150923-36" for row in fault_notices)
    assert REQUIRED_HEADERS.issubset(set(list_schema.headers.values()))
