import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.daily_inspection.not_submitted import (
    DailyInspectionNotSubmittedQuery,
    FIELDS,
    STATUSES,
    STATUS_FILTER,
)
from mmis_connector.parser import parse_maximo_table
from tools.mmis_development import query_daily_inspection_work_orders_not_submitted_for_approval as tool


STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-11-02_query-daily-inspection-work-orders-not-submitted-for-approval"
    r"\dom\2026-11-02T071923-275.html"
)


def _page(
    start: int, end: int, total: int, *, next_page: bool,
    work_order_offset: int = 0, depot: str = "新竹機務段",
    status: str = "執行中已派工",
) -> str:
    headers = "".join(
        f'<span id="table_ttrow_[C:{i}]_ttitle-lb">{field}</span>'
        for i, field in enumerate((*FIELDS[:-1], "逾期標註?"), start=1)
    )

    def row_html(number: int) -> str:
        values = {
            1: depot,
            5: str(number + work_order_offset),
            8: status,
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
    monkeypatch.setattr(
        query.events, "load_app_with_response",
        lambda **kwargs: (STATE, _page(1, 1, 1, next_page=False)),
    )
    calls: list[dict[str, Any]] = []
    responses = iter(["", "", "", "", *pages])

    def fake_post_event(**kwargs: Any) -> str:
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(query, "_post_event", fake_post_event)
    return query, calls


def test_reads_all_31_records_and_uses_current_date(monkeypatch: pytest.MonkeyPatch) -> None:
    assert STATUS_FILTER == (
        "執行中已派工,執行中未派工,完工待回報,工單初始,工單取消,"
        "工單取消核簽中,工單取消申請,工單結案,工單退回,檢修完成"
    )
    query, calls = _query(
        monkeypatch,
        [_page(1, 30, 31, next_page=True), _page(31, 31, 31, next_page=False)],
    )
    result = query.run(today=datetime(2026, 11, 2))

    assert result["count"] == 31
    assert [row["工作單"] for row in result["records"]] == [str(i) for i in range(1, 32)]
    assert list(result["records"][0]) == list(FIELDS)
    assert result["records"][0]["逾期標註"] is False
    assert [(call["event_type"], call["value"]) for call in calls[:5]] == [
        ("setvalue", "新竹機務段"),
        ("setvalue", ""),
        ("setvalue", "<2026/11/02"),
        ("setvalue", STATUS_FILTER),
        ("filterrows", ""),
    ]
    assert calls[-1]["target_id"] == "table-ti7"
    assert calls[-1]["xhr_seq"] == 7
    assert all(call["value"] != "useAllRecsQuery_OPTION" for call in calls)
    assert any(
        call["event_type"] == "setvalue"
        and call["target_id"] == "table_tfrow_[C:2]_txt-tb"
        and call["value"] == ""
        for call in calls
    )


@pytest.mark.parametrize("status", STATUSES)
def test_accepts_each_requested_status(monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    query, _ = _query(monkeypatch, [_page(1, 1, 1, next_page=False, status=status)])
    result = query.run(today=datetime(2026, 11, 2))
    assert result["records"][0]["工作單狀態"] == status


def test_rejects_status_outside_requested_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    query, _ = _query(monkeypatch, [_page(1, 1, 1, next_page=False, status="核簽中")])
    with pytest.raises(MMISClientError, match="不符合查詢條件"):
        query.run(today=datetime(2026, 11, 2))


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


def _record(work_order: str, overdue: bool = False) -> dict[str, Any]:
    record = {field: field for field in FIELDS}
    record["工作單"] = work_order
    record["逾期標註"] = overdue
    return record


def test_snapshot_replaces_old_rows_and_keeps_all_fields(tmp_path: Path) -> None:
    database = tmp_path / "data" / "work_orders.db"
    tool.replace_records([_record("old")], database)
    assert tool.replace_records([_record("new", True)], database) == 1

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info({tool.TABLE_NAME})")]
        rows = connection.execute(f"SELECT * FROM {tool.TABLE_NAME}").fetchall()
    assert columns == list(tool.DATABASE_FIELDS)
    assert len(rows) == 1
    assert dict(rows[0]) == {**_record("new", True), "逾期標註": 1, "備註欄": ""}

    assert tool.replace_records([], database) == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute(f"SELECT COUNT(*) FROM {tool.TABLE_NAME}").fetchone()[0] == 0


def test_snapshot_rolls_back_on_insert_failure(tmp_path: Path) -> None:
    database = tmp_path / "work_orders.db"
    tool.replace_records([_record("old")], database)

    with pytest.raises(sqlite3.IntegrityError):
        tool.replace_records([_record("duplicate"), _record("duplicate")], database)

    with sqlite3.connect(database) as connection:
        rows = connection.execute(f'SELECT "工作單" FROM {tool.TABLE_NAME}').fetchall()
    assert rows == [("old",)]


def test_marks_only_dispatched_orders_with_complete_records_and_no_vehicle_room_staff(
    tmp_path: Path,
) -> None:
    database = tmp_path / "work_orders.db"
    orders = [
        ("notify", "執行中已派工"),
        ("incomplete", "執行中已派工"),
        ("inspector", "執行中已派工"),
        ("technician", "執行中已派工"),
        ("other-status", "檢修完成"),
    ]
    records = []
    for number, status in orders:
        record = _record(number)
        record["工作單狀態"] = status
        records.append(record)
    tool.replace_records(records, database)
    seen: list[str] = []

    def read_detail(number: str) -> dict[str, Any]:
        seen.append(number)
        staff = []
        if number == "notify":
            staff.append({"人員群組": "檢查室", "工作角色": "檢查員", "員工代號": "3", "姓名": "丙"})
        if number == "inspector":
            staff.append({"人員群組": "檢車室", "工作角色": "檢查員", "員工代號": "1", "姓名": "甲"})
        if number == "technician":
            staff.append({"人員群組": "檢車室", "工作角色": "修繕人員", "員工代號": "2", "姓名": "乙"})
        return {
            "work_order": number,
            "success": True,
            "maintenance_records_complete": number != "incomplete",
            "maintenance_personnel": {"records": staff},
        }

    reader = SimpleNamespace(run=read_detail)
    assert tool.mark_orders_requiring_personnel(database, reader) == 1
    assert seen == ["notify", "incomplete", "inspector", "technician"]
    with sqlite3.connect(database) as connection:
        notes = dict(connection.execute(f'SELECT "工作單", "備註欄" FROM {tool.TABLE_NAME}'))
    assert notes == {number: "通知檢車室" if number == "notify" else "" for number, _ in orders}


def test_detail_failure_does_not_write_partial_notes(tmp_path: Path) -> None:
    database = tmp_path / "work_orders.db"
    records = []
    for number in ("first", "second"):
        record = _record(number)
        record["工作單狀態"] = "執行中已派工"
        records.append(record)
    tool.replace_records(records, database)

    def read_detail(number: str) -> dict[str, Any]:
        if number == "second":
            raise MMISClientError("明細查詢失敗")
        return {
            "work_order": number, "success": True,
            "maintenance_records_complete": True,
            "maintenance_personnel": {"records": []},
        }

    with pytest.raises(MMISClientError, match="明細查詢失敗"):
        tool.mark_orders_requiring_personnel(database, SimpleNamespace(run=read_detail))
    with sqlite3.connect(database) as connection:
        notes = connection.execute(f'SELECT "備註欄" FROM {tool.TABLE_NAME}').fetchall()
    assert notes == [("",), ("",)]


def test_cli_enriches_database_using_the_same_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(tool, "DATABASE_PATH", tmp_path / "work_orders.db")
    session = object()
    monkeypatch.setattr(tool, "MMISConfig", SimpleNamespace(from_env=lambda: object()))
    monkeypatch.setattr(tool, "MMISSession", lambda config: session)
    record = _record("115-1A-80516")
    record["工作單狀態"] = "執行中已派工"
    monkeypatch.setattr(
        tool, "DailyInspectionNotSubmittedQuery",
        lambda client: SimpleNamespace(run=lambda: {"records": [record]})
        if client is session else pytest.fail("清單查詢未重用 session"),
    )
    monkeypatch.setattr(
        tool, "DailyInspectionInspectionRecordReader",
        lambda client: SimpleNamespace(run=lambda number: {
            "work_order": number,
            "success": True,
            "maintenance_records_complete": True,
            "maintenance_personnel": {"records": []},
        }) if client is session else pytest.fail("明細查詢未重用 session"),
    )

    assert tool.main([]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Status: SUCCESS",
        "Records found: 1",
        "Vehicle room notifications: 1",
        f"Database path: {tool.DATABASE_RELATIVE_PATH.as_posix()}",
    ]
    with sqlite3.connect(tool.DATABASE_PATH) as connection:
        note = connection.execute(f'SELECT "備註欄" FROM {tool.TABLE_NAME}').fetchone()[0]
    assert note == "通知檢車室"


def test_cli_prints_english_result_and_writes_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(tool, "DATABASE_PATH", tmp_path / "data" / "work_orders.db")
    monkeypatch.setattr(tool, "MMISConfig", SimpleNamespace(from_env=lambda: object()))
    monkeypatch.setattr(tool, "MMISSession", lambda config: object())
    monkeypatch.setattr(
        tool,
        "DailyInspectionNotSubmittedQuery",
        lambda session: SimpleNamespace(run=lambda: {"records": [_record("123")]}),
    )

    assert tool.main([]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Status: SUCCESS",
        "Records found: 1",
        "Vehicle room notifications: 0",
        f"Database path: {tool.DATABASE_RELATIVE_PATH.as_posix()}",
    ]
    with sqlite3.connect(tool.DATABASE_PATH) as connection:
        assert connection.execute(f'SELECT "工作單" FROM {tool.TABLE_NAME}').fetchone() == ("123",)

    assert tool.main(["unexpected"]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "Status: FAILED",
        "Records found: unavailable",
        f"Database path: {tool.DATABASE_RELATIVE_PATH.as_posix()}",
        "Error: MMISClientError",
    ]


def test_export_xlsx_sorts_then_numbers_and_formats(tmp_path: Path) -> None:
    from openpyxl import load_workbook

    database = tmp_path / "work_orders.db"
    records = []
    for order, date, train, vehicle in (
        ("WO-3", "2026/11/03", "B", "720"),
        ("WO-2", "2026/11/02", "A", "720"),
        ("WO-1", "2026/11/02", "A", "710"),
        ("WO-4", "2026/11/02", "B", "710"),
        ("WO-0", "2026/11/01", "A", "700"),
    ):
        record = _record(order)
        record.update({"檢修日期": date, "車次": train, "車組/車號": vehicle})
        records.append(record)
    tool.replace_records(records, database)
    with sqlite3.connect(database) as connection:
        connection.executemany(
            f'UPDATE {tool.TABLE_NAME} SET "備註欄" = ? WHERE "工作單" = ?',
            [(tool.NOTIFICATION_NOTE, f"WO-{number}") for number in range(1, 5)],
        )

    exported = tool.export_snapshot_xlsx(
        database, len(records), output_directory=tmp_path,
        now=datetime(2026, 11, 3),
    )
    output = Path(exported["output_file"])
    assert output.name == "檢車室未填檢修人員日檢工單_程式產生1103.xlsx"
    assert exported["columns_exported"] == 5
    assert exported["records_exported"] == 4
    workbook = load_workbook(output)
    try:
        sheet = workbook.active
        assert list(sheet.values) == [
            tool.XLSX_COLUMNS,
            (1, "710", "WO-1", "A", "2026/11/02"),
            (2, "720", "WO-2", "A", "2026/11/02"),
            (3, "710", "WO-4", "B", "2026/11/02"),
            (4, "720", "WO-3", "B", "2026/11/03"),
        ]
        assert [sheet.column_dimensions[column].width for column in "ABCDE"] == [
            5.7, 11.8, 17.9, 6.5, 14.5,
        ]
        assert [sheet.row_dimensions[row].height for row in range(1, sheet.max_row + 1)] == [
            15.5,
        ] * sheet.max_row
        assert sheet["A1"].font.name == sheet["A2"].font.name == "微軟正黑體"
        assert sheet["A1"].font.sz == sheet["A2"].font.sz == 12
        assert sheet["A1"].font.bold is True
        assert sheet["A2"].font.bold is False
        assert sheet["A1"].alignment.horizontal == "center"
        assert sheet["B2"].alignment.horizontal == "left"
    finally:
        workbook.close()


def test_export_xlsx_with_no_notifications_keeps_header(tmp_path: Path) -> None:
    from openpyxl import load_workbook

    database = tmp_path / "work_orders.db"
    tool.replace_records([_record("WO-1")], database)

    exported = tool.export_snapshot_xlsx(
        database, 1, output_directory=tmp_path, now=datetime(2026, 11, 3),
    )

    assert exported["records_exported"] == 0
    workbook = load_workbook(exported["output_file"])
    try:
        assert list(workbook.active.values) == [tool.XLSX_COLUMNS]
    finally:
        workbook.close()


def test_cli_export_flag_uses_saved_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(tool, "DATABASE_PATH", tmp_path / "work_orders.db")
    monkeypatch.setattr(tool, "MMISConfig", SimpleNamespace(from_env=lambda: object()))
    monkeypatch.setattr(tool, "MMISSession", lambda config: object())
    monkeypatch.setattr(
        tool, "DailyInspectionNotSubmittedQuery",
        lambda session: SimpleNamespace(run=lambda: {"records": [_record("WO-1")]}),
    )
    exported_path = tmp_path / "result.xlsx"

    def fake_export(path: Path, count: int) -> dict[str, Any]:
        assert path == tool.DATABASE_PATH
        assert count == 1
        with sqlite3.connect(path) as connection:
            assert connection.execute(f'SELECT "工作單" FROM {tool.TABLE_NAME}').fetchone() == ("WO-1",)
        return {"output_file": str(exported_path)}

    monkeypatch.setattr(tool, "export_snapshot_xlsx", fake_export)
    assert tool.main(["--export-xlsx"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == f"Excel path: {exported_path}"
    assert tool.main(["--export-xlsx", "--export-xlsx"]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "Error: MMISClientError"
