import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.daily_inspection.unassigned import UnassignedDailyInspectionWorkOrderQuery
from tools.mmis_development.auto_delete_duplicate_daily_inspection_work_orders import (
    PENDING_CANCELLATION,
    replace_records,
    update_duplicate_work_orders,
)

STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
HEADERS = ("檢修段", "配屬段", "車組/車號", "檢修級別", "工作單", "車次",
           "檢修單位", "工作單狀態", "處理人員", "預計檢修(進廠)日", "檢修日期")


def page(start: int, end: int, total: int, next_page: bool) -> str:
    headers = "".join(
        f'<span id="table_ttrow_[C:{i}]_ttitle-lb">{name}</span>'
        for i, name in enumerate(HEADERS, 1)
    )
    rows = ""
    for number in range(start, end + 1):
        values = {2: "新竹機務段", 3: "EMU700", 5: str(number),
                  8: "執行中未派工", 10: "2026/11/05"}
        cells = "".join(
            f'<td id="table_tdrow_[C:{column}]-c[R:{number-start}]">'
            f'<span>{values.get(column, name)}</span></td>'
            for column, name in enumerate(HEADERS, 1)
        )
        rows += f'<tr id="table_tbod_tdrow-tr[R:{number-start}]">{cells}</tr>'
    control = '<a id="table-ti7"><img id="table-ti7_img" src="tablebtn_next_on.gif"></a>' if next_page else ""
    return headers + f'<label id="table-lb3" class="tCount">{start} - {end}/{total}</label>' + control + rows


def test_query_collects_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    query = UnassignedDailyInspectionWorkOrderQuery(SimpleNamespace(state=STATE))
    monkeypatch.setattr(query.events, "load_app_with_response", lambda **kw: (STATE, page(1, 1, 1, False)))
    calls = []
    responses = iter(["", "", page(1, 30, 31, True), page(31, 31, 31, False)])

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(query, "_post_event", post)
    rows = query.run()
    assert len(rows) == 31
    assert rows[-1] == {"車組/車號": "EMU700", "工作單": "31", "預計檢修(進廠)日": "2026/11/05"}
    assert [call["value"] for call in calls[:2]] == ["新竹機務段", "執行中未派工"]
    assert calls[-1]["target_id"] == "table-ti7"


def test_snapshot_replaces_old_rows_and_preserves_on_error(tmp_path: Path) -> None:
    db = tmp_path / "snapshot.db"
    row = {"車組/車號": "EMU700", "工作單": "1", "預計檢修(進廠)日": "2026/11/05"}
    assert replace_records([row], db) == 1
    with sqlite3.connect(db) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(daily_inspection_work_orders)")]
        values = connection.execute('SELECT "車組/車號", "工作單", "預計檢修(進廠)日", "查詢時間", "開單日期", "執行結果" FROM daily_inspection_work_orders').fetchone()
    assert columns == ["車組/車號", "工作單", "預計檢修(進廠)日", "查詢時間", "開單日期", "執行結果"]
    assert values[:3] == ("EMU700", "1", "2026/11/05")
    assert values[3] and values[4:] == ("", "")
    with pytest.raises(KeyError):
        replace_records([{}], db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_inspection_work_orders").fetchone()[0] == 1
    assert replace_records([], db) == 0
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_inspection_work_orders").fetchone()[0] == 0


def test_duplicate_group_marks_only_older_work_order(tmp_path: Path) -> None:
    db = tmp_path / "duplicates.db"
    records = [
        {"車組/車號": "EMU929", "工作單": "115-1A-81454", "預計檢修(進廠)日": "2026/11/01"},
        {"車組/車號": "EMU929", "工作單": "115-1A-90001", "預計檢修(進廠)日": "2026/11/02"},
        {"車組/車號": "EMU700", "工作單": "115-1A-70001", "預計檢修(進廠)日": "2026/11/02"},
    ]
    replace_records(records, db)
    details = {
        "115-1A-81454": {"工作單": "115-1A-81454", "車組/車號": "EMU929", "開單日期": "2026/11/01 08:00"},
        "115-1A-90001": {"工作單": "115-1A-90001", "車組/車號": "EMU929", "開單日期": "2026/11/02 09:00"},
    }
    result = update_duplicate_work_orders(db, details.__getitem__)

    assert result.duplicate_groups == 1
    assert result.dates_written == 2
    assert result.cancellation_orders == ("115-1A-81454",)
    assert not result.incomplete_groups
    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            'SELECT "工作單", "開單日期", "執行結果" FROM daily_inspection_work_orders ORDER BY "工作單"'
        ).fetchall()
    assert rows == [
        ("115-1A-70001", "", "無重複"),
        ("115-1A-81454", "2026/11/01 08:00", PENDING_CANCELLATION),
        ("115-1A-90001", "2026/11/02 09:00", ""),
    ]


def test_single_vehicle_marks_no_duplicate_without_detail_lookup(tmp_path: Path) -> None:
    db = tmp_path / "single.db"
    replace_records(
        [
            {"車組/車號": "EMU700", "工作單": "A-1", "預計檢修(進廠)日": "2026/11/01"},
            {"車組/車號": "", "工作單": "B-1", "預計檢修(進廠)日": "2026/11/01"},
        ],
        db,
    )

    def fail_if_called(_: str) -> dict[str, str]:
        raise AssertionError("single vehicles must not trigger detail lookup")

    result = update_duplicate_work_orders(db, fail_if_called)

    assert result.duplicate_groups == 0
    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            'SELECT "工作單", "執行結果" FROM daily_inspection_work_orders ORDER BY "工作單"'
        ).fetchall()
    assert rows == [("A-1", "無重複"), ("B-1", "")]


def test_incomplete_or_tied_duplicate_groups_are_not_marked(tmp_path: Path) -> None:
    db = tmp_path / "incomplete.db"
    records = [
        {"車組/車號": "EMU929", "工作單": "A-1", "預計檢修(進廠)日": "2026/11/01"},
        {"車組/車號": "EMU929", "工作單": "A-2", "預計檢修(進廠)日": "2026/11/02"},
        {"車組/車號": "EMU700", "工作單": "B-1", "預計檢修(進廠)日": "2026/11/01"},
        {"車組/車號": "EMU700", "工作單": "B-2", "預計檢修(進廠)日": "2026/11/02"},
    ]
    replace_records(records, db)

    def read_detail(work_order: str) -> dict[str, str]:
        if work_order == "A-2":
            raise MMISClientError("temporary query failure")
        vehicle = "EMU929" if work_order.startswith("A") else "EMU700"
        date = (
            "2026/11/01 08:00"
            if work_order.startswith("B") or work_order.endswith("1")
            else "2026/11/02 08:00"
        )
        return {"工作單": work_order, "車組/車號": vehicle, "開單日期": date}

    result = update_duplicate_work_orders(db, read_detail)

    assert result.incomplete_groups == ("EMU929",)
    assert result.ambiguous_groups == ("EMU700",)
    assert not result.cancellation_orders
    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            'SELECT "工作單", "執行結果" FROM daily_inspection_work_orders ORDER BY "工作單"'
        ).fetchall()
    assert rows == [("A-1", ""), ("A-2", ""), ("B-1", ""), ("B-2", "")]


def test_duplicate_update_refuses_to_write_into_a_replaced_snapshot(tmp_path: Path) -> None:
    db = tmp_path / "replaced.db"
    original = [
        {"車組/車號": "EMU929", "工作單": "A-1", "預計檢修(進廠)日": "2026/11/01"},
        {"車組/車號": "EMU929", "工作單": "A-2", "預計檢修(進廠)日": "2026/11/02"},
    ]
    replace_records(original, db)
    replacement = [
        {"車組/車號": "EMU929", "工作單": "A-1", "預計檢修(進廠)日": "2026/11/03"},
        {"車組/車號": "EMU929", "工作單": "A-2", "預計檢修(進廠)日": "2026/11/04"},
    ]

    def read_detail(work_order: str) -> dict[str, str]:
        if work_order == "A-1":
            replace_records(replacement, db)
        return {
            "工作單": work_order,
            "車組/車號": "EMU929",
            "開單日期": "2026/11/01 08:00" if work_order == "A-1" else "2026/11/02 08:00",
        }

    with pytest.raises(MMISClientError, match="快照在明細查詢期間已更新"):
        update_duplicate_work_orders(db, read_detail)

    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            'SELECT "工作單", "開單日期", "執行結果" FROM daily_inspection_work_orders ORDER BY "工作單"'
        ).fetchall()
    assert rows == [("A-1", "", ""), ("A-2", "", "")]


def test_failed_rerun_clears_stale_dates_and_cancellation_marks(tmp_path: Path) -> None:
    db = tmp_path / "rerun.db"
    replace_records(
        [
            {"車組/車號": "EMU929", "工作單": "A-1", "預計檢修(進廠)日": "2026/11/01"},
            {"車組/車號": "EMU929", "工作單": "A-2", "預計檢修(進廠)日": "2026/11/02"},
        ],
        db,
    )
    with sqlite3.connect(db) as connection:
        connection.execute(
            'UPDATE daily_inspection_work_orders SET "開單日期" = ?, "執行結果" = ? WHERE "工作單" = ?',
            ("2026/11/01 08:00", PENDING_CANCELLATION, "A-1"),
        )
        connection.execute(
            'UPDATE daily_inspection_work_orders SET "開單日期" = ? WHERE "工作單" = ?',
            ("2026/11/02 08:00", "A-2"),
        )

    def read_detail(work_order: str) -> dict[str, str]:
        if work_order == "A-2":
            raise MMISClientError("temporary query failure")
        return {"工作單": "A-1", "車組/車號": "EMU929", "開單日期": "2026/11/01 08:00"}

    result = update_duplicate_work_orders(db, read_detail)

    assert result.incomplete_groups == ("EMU929",)
    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            'SELECT "工作單", "開單日期", "執行結果" FROM daily_inspection_work_orders ORDER BY "工作單"'
        ).fetchall()
    assert rows == [("A-1", "2026/11/01 08:00", ""), ("A-2", "", "")]


def test_unexpected_reader_error_is_not_treated_as_incomplete_data(tmp_path: Path) -> None:
    db = tmp_path / "reader-error.db"
    replace_records(
        [
            {"車組/車號": "EMU929", "工作單": "A-1", "預計檢修(進廠)日": "2026/11/01"},
            {"車組/車號": "EMU929", "工作單": "A-2", "預計檢修(進廠)日": "2026/11/02"},
        ],
        db,
    )

    def read_detail(_: str) -> dict[str, str]:
        raise RuntimeError("programming error")

    with pytest.raises(RuntimeError, match="programming error"):
        update_duplicate_work_orders(db, read_detail)
