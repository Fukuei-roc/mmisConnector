from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.periodic_inspection.query import (
    LatestPeriodicInspectionWorkOrderQuery,
)
from tools.mmis_development import query_latest_periodic_inspection_work_order as tool


STATE = PageState("session", 3, "csrf", "zz_pmwo", "https://example.test/app")
HEADERS = {
    1: "車組/車號",
    3: "檢修級別",
    5: "工作單",
    7: "檢修單位",
    8: "工作單狀態",
    12: "檢修日期",
}


def table(
    records: list[tuple[str, str, str, str]],
    *,
    start: int = 1,
    total: int | None = None,
    next_page: bool = False,
) -> str:
    total = len(records) if total is None else total
    headers = "".join(
        f'<span id="list_ttrow_[C:{column}]_ttitle-lb">{label}</span>'
        for column, label in HEADERS.items()
    )
    rows = []
    for index, (vehicle, level, work_order, date) in enumerate(records):
        values = {
            1: vehicle,
            3: level,
            5: work_order,
            7: "檢查室",
            8: "工單結案",
            12: date,
        }
        cells = "".join(
            f'<td id="list_tdrow_[C:{column}]-c[R:{index}]">'
            f'<span id="list_{column}_ttxt-lb[R:{index}]">{value}</span></td>'
            for column, value in values.items()
        )
        rows.append(f'<tr id="list_tbod_tdrow-tr[R:{index}]">{cells}</tr>')
    end = start + len(records) - 1 if records else 0
    count = f'<label id="list-lb3" class="tCount">{start if records else 0} - {end}/{total}</label>'
    next_button = (
        '<a id="list-ti2"><img id="list-ti2_img" src="tablebtn_next_on.gif"></a>'
        if next_page else ""
    )
    empty = "沒有要顯示的列。" if not records else ""
    return headers + count + "".join(rows) + next_button + empty


def run_query(monkeypatch: pytest.MonkeyPatch, *pages: str):
    client = SimpleNamespace(state=STATE)
    query = LatestPeriodicInspectionWorkOrderQuery(client)
    calls = []
    responses = iter(
        ["<div>mainrec_menus</div>", table([]), "", "", "", "", *pages]
    )
    monkeypatch.setattr(
        query.events,
        "load_app_with_response",
        lambda **kwargs: (STATE, ""),
    )

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(query.events, "post", post)
    return query, calls


def test_latest_row_across_pages_and_recorded_event_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = table(
        [("EMU813", "2A", "115-2A-68000-001", "2026/09/01")],
        total=2,
        next_page=True,
    )
    second = table(
        [("EMU813", "3A", "115-3A-68700-001", "2026/09/14")],
        start=2,
        total=2,
    )
    query, calls = run_query(monkeypatch, first, second)

    assert query.run(" 813 ") == {
        "車組/車號": "EMU813",
        "檢修級別": "3A",
        "工作單": "115-3A-68700-001",
        "檢修日期": "2026/09/14",
    }
    assert [(call["event_type"], call["value"]) for call in calls] == [
        ("click", ""),
        ("click", "useAllRecsQuery_OPTION"),
        ("setvalue", "813"),
        ("setvalue", "2A,3A"),
        ("setvalue", "檢查室"),
        ("setvalue", "工單結案,簽核中"),
        ("filterrows", ""),
        ("click", ""),
    ]
    assert [call["target_id"] for call in calls[2:7]] == [
        "list_tfrow_[C:1]_txt-tb",
        "list_tfrow_[C:3]_txt-tb",
        "list_tfrow_[C:7]_txt-tb",
        "list_tfrow_[C:8]_txt-tb",
        "list_tbod_tfrow-tr",
    ]
    assert calls[-1]["target_id"] == "list-ti2"
    assert [call["xhr_seq"] for call in calls] == list(range(1, 9))


def test_latest_date_wins_even_when_rows_are_unsorted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query, _ = run_query(
        monkeypatch,
        table([
            ("EMU701", "2A", "115-2A-74357-001", "2026/10/15"),
            ("EMU701", "3A", "115-3A-70001", "2026/09/01"),
        ]),
    )
    assert query.run("701")["工作單"] == "115-2A-74357-001"


def test_numeric_vehicle_does_not_match_another_trains_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query, _ = run_query(
        monkeypatch,
        table([
            ("EMU1701", "2A", "115-2A-99999", ""),
            ("EMU701", "2A", "115-2A-74357-001", "2026/10/15"),
        ]),
    )
    assert query.run("701")["工作單"] == "115-2A-74357-001"


def test_only_other_vehicle_returns_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    query, _ = run_query(
        monkeypatch,
        table([("EMU1701", "2A", "115-2A-99999", "2026/11/01")]),
    )
    with pytest.raises(MMISClientError, match="找不到車組/車號 701"):
        query.run("701")


def test_rejects_server_row_with_unrequested_inspection_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query, _ = run_query(
        monkeypatch,
        table([("EMU813", "1A", "115-1A-99999", "2026/11/01")]),
    )
    with pytest.raises(MMISClientError, match="結果與篩選條件不符"):
        query.run("813")


def test_same_date_uses_work_order_number_as_tie_break(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query, _ = run_query(
        monkeypatch,
        table([
            ("EMU701", "2A", "115-2A-10001", "2026/10/15"),
            ("EMU701", "2A", "115-2A-10002", "2026/10/15"),
        ]),
    )
    assert query.run("701")["工作單"] == "115-2A-10002"


@pytest.mark.parametrize(
    ("page", "message"),
    [
        (table([]), "找不到車組/車號"),
        (table([("EMU701", "2A", "115-2A-1", "2026/02/30")]), "檢修日期無效"),
        (table([("EMU701", "2A", "115-2A-1", "2026/2/03")]), "檢修日期格式無效"),
        (table([("EMU701", "2A", "115-2A-1", "2026/01/01")], total=2), "找不到下一頁"),
    ],
)
def test_rejects_empty_or_incomplete_results(
    monkeypatch: pytest.MonkeyPatch, page: str, message: str
) -> None:
    query, _ = run_query(monkeypatch, page)
    with pytest.raises(MMISClientError, match=message):
        query.run("701")


def test_cli_prints_only_four_fields(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    expected = {
        "車組/車號": "EMU701",
        "檢修級別": "2A",
        "工作單": "115-2A-74357-001",
        "檢修日期": "2026/10/15",
    }
    monkeypatch.setattr(tool, "execute", lambda args: expected)
    assert tool.main(["701"]) == 0
    assert json.loads(capsys.readouterr().out) == expected


def test_cli_rejects_missing_argument(capsys) -> None:
    assert tool.main([]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert "用法" in output["message"]


RECORDED_HAR = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-27_query-latest-maintenance-work-orders\raw.har"
)


@pytest.mark.skipif(not RECORDED_HAR.exists(), reason="本機未提供定期檢修錄製 HAR")
def test_recorded_filtered_response_matches_parser_contract() -> None:
    from mmis_connector.parser import parse_maximo_page_info, parse_maximo_table

    har = json.loads(RECORDED_HAR.read_text(encoding="utf-8"))
    filtered = [
        entry for entry in har["log"]["entries"]
        if "filterrows" in entry["request"].get("postData", {}).get("text", "")
    ]
    assert len(filtered) == 1
    response = filtered[0]["response"]["content"]["text"]
    schema, rows = parse_maximo_table(
        response,
        required_headers={"車組/車號", "檢修級別", "工作單", "檢修日期"},
    )
    assert schema is not None
    assert parse_maximo_page_info(
        response, table_prefix=schema.prefix, context_name="定期檢修工單"
    ).total == len(rows) == 19
    latest = max(rows, key=lambda row: (row["檢修日期"], row["工作單"]))
    assert {field: latest[field] for field in ("車組/車號", "檢修級別", "工作單", "檢修日期")} == {
        "車組/車號": "EMU813",
        "檢修級別": "3A",
        "工作單": "115-3A-68700-001",
        "檢修日期": "2026/09/14",
    }
