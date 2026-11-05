from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from openpyxl import load_workbook

from mmis_connector.auth import MMISClientError
from mmis_connector.overdue_work_orders import FIELDS, OverdueWorkOrderQuery
from tools.mmis_development import audit_overdue_work_orders as tool
from tools.mmis_development.audit_overdue_work_orders import replace_records


DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings\2026-11-05_query-overdue-work-orders"
    r"\dom\2026-11-05T015548-891.html"
)


def synthetic_page(order: str, position: int, *, next_page: bool) -> str:
    headers = "".join(
        f'<span id="orders_ttrow_[C:{index}]_ttitle-lb">{field}</span>'
        for index, field in enumerate(FIELDS, start=1)
    )
    cells = "".join(
        f'<td id="orders_tdrow_[C:{index}]-c[R:0]">'
        f'{order if field == "工單編號" else field}</td>'
        for index, field in enumerate(FIELDS, start=1)
    )
    button = "on" if next_page else "off"
    return (
        headers
        + f'<div id="orders_tbod_tdrow-tr[R:0]">{cells}</div>'
        + f'<label id="orders-lb3" class="tCount">{position} - {position}/2</label>'
        + f'<a id="orders-ti7"><img id="orders-ti7_img" '
        + f'src="tablebtn_next_{button}.gif"></a>'
    )


def test_query_reads_every_page_without_recording() -> None:
    query = OverdueWorkOrderQuery.__new__(OverdueWorkOrderQuery)

    class Events:
        def load_app_with_response(self, **kwargs):
            assert kwargs["app_value"] == "ZZ_WO_OVERDUE"
            return object(), synthetic_page("WO-1", 1, next_page=True)

        def post(self, **kwargs):
            assert kwargs["target_id"] == "orders-ti7"
            return synthetic_page("WO-2", 2, next_page=False)

    query.events = Events()
    query.client = type("Client", (), {"state": None})()
    assert [row["工單編號"] for row in query.run()] == ["WO-1", "WO-2"]


def test_recorded_page_yields_all_eight_columns() -> None:
    if not DOM.exists():
        pytest.skip("local recording is unavailable")
    html = DOM.read_text(encoding="utf-8")
    query = OverdueWorkOrderQuery.__new__(OverdueWorkOrderQuery)

    class Events:
        def load_app_with_response(self, **kwargs):
            assert kwargs["app_value"] == "ZZ_WO_OVERDUE"
            return object(), html

    query.events = Events()
    query.client = type("Client", (), {"state": None})()
    records = query.run()
    assert len(records) == 10
    assert all(tuple(record) == FIELDS for record in records)
    assert records[0]["工單編號"]


def test_replacement_clears_old_rows_and_notes(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    first = {field: "x" for field in FIELDS}
    first["工單編號"] = "WO-1"
    second = {field: "y" for field in FIELDS}
    second["工單編號"] = "WO-2"
    replace_records([first], path)
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE overdue_work_orders SET "備註" = ?', ("edited",))
    assert replace_records([second], path) == 1
    with sqlite3.connect(path) as connection:
        columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(overdue_work_orders)"))
        rows = connection.execute('SELECT "工單編號", "備註" FROM overdue_work_orders').fetchall()
    assert columns == (*FIELDS, "備註")
    assert rows == [("WO-2", "")]


def test_failed_replacement_rolls_back_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    old = {field: "old" for field in FIELDS}
    old["工單編號"] = "WO-OLD"
    replace_records([old], path)
    broken = dict(old)
    broken.pop("逾期天數")
    with pytest.raises(KeyError):
        replace_records([broken], path)
    with sqlite3.connect(path) as connection:
        rows = connection.execute('SELECT "工單編號" FROM overdue_work_orders').fetchall()
    assert rows == [("WO-OLD",)]


@pytest.mark.parametrize("args", [[], ["--export-xlsx"]])
def test_audit_queries_only_periodic_orders_and_prints_noted_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> None:
    path = tmp_path / "overdue.db"
    records = []
    for number, level in (
        ("115-2A-74886", "2A"),
        ("115-1A-1", "1A"),
        ("115-3A-75840", "3A"),
        ("115-3A-75841", "3A"),
    ):
        record = {field: "value" for field in FIELDS}
        record.update({"工單編號": number, "檢修級別": level})
        records.append(record)
    session = object()
    queried = []

    class OverdueQuery:
        def __init__(self, client):
            assert client is session

        def run(self):
            return records

    class StatusQuery:
        def __init__(self, client):
            assert client is session

        def run(self, order):
            queried.append(order)
            statuses = (
                ("工單退回", "核簽中", "執行中未派工")
                if order == "115-2A-74886"
                else ("工單退回",) if order == "115-3A-75840" else ("工單結案",)
            )
            return {"records": [
                {"工作單": f"{order}-{index:03}", "工作單狀態": status}
                for index, status in enumerate(statuses, start=1)
            ]}

    monkeypatch.setattr(tool, "DATABASE_PATH", path)
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda config: session)
    monkeypatch.setattr(tool, "OverdueWorkOrderQuery", OverdueQuery)
    monkeypatch.setattr(tool, "CompletePeriodicInspectionWorkOrderStatusQuery", StatusQuery)
    monkeypatch.setenv("UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR", str(tmp_path))

    assert tool.main(args) == 0
    assert queried == ["115-2A-74886", "115-3A-75840", "115-3A-75841"]
    with sqlite3.connect(path) as connection:
        notes = dict(connection.execute(
            'SELECT "工單編號", "備註" FROM overdue_work_orders ORDER BY rowid'
        ))
    assert notes == {
        "115-2A-74886": (
            "115-2A-74886-001(工單退回),115-2A-74886-003(執行中未派工)"
        ),
        "115-1A-1": "",
        "115-3A-75840": "115-3A-75840-001(工單退回)",
        "115-3A-75841": "",
    }
    output = capsys.readouterr().out.splitlines()
    printed = json.loads(output[-1])
    assert [row["工單編號"] for row in printed] == ["115-2A-74886", "115-3A-75840"]
    assert [row["備註"] for row in printed] == [
        notes["115-2A-74886"], notes["115-3A-75840"]
    ]
    assert all(tuple(row) == (*FIELDS, "備註") for row in printed)
    exports = list(tmp_path.glob("*.xlsx"))
    if args:
        assert len(exports) == 1
        assert f"Excel path: {exports[0]}" in output
        with sqlite3.connect(path) as connection:
            saved_rows = connection.execute(
                'SELECT * FROM overdue_work_orders ORDER BY rowid'
            ).fetchall()
        workbook = load_workbook(exports[0])
        try:
            assert list(workbook.active.values) == [
                tool.DATABASE_FIELDS,
                *(tuple(value or None for value in saved_rows[index]) for index in (1, 0, 2, 3)),
            ]
        finally:
            workbook.close()
    else:
        assert exports == []
        assert not any(line.startswith("Excel path:") for line in output)


def test_status_query_failure_leaves_new_snapshot_without_partial_notes(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    records = []
    for number in ("115-2A-74886", "115-3A-75840"):
        record = {field: "value" for field in FIELDS}
        record.update({"工單編號": number, "檢修級別": "2A"})
        records.append(record)
    replace_records(records, path)

    class StatusQuery:
        def run(self, order):
            if order == "115-3A-75840":
                raise RuntimeError("MMIS error")
            return {"records": [{
                "工作單": "115-2A-74886-001", "工作單狀態": "工單退回"
            }]}

    with pytest.raises(RuntimeError, match="MMIS error"):
        tool.annotate_periodic_records(StatusQuery(), path)
    with sqlite3.connect(path) as connection:
        notes = connection.execute(
            'SELECT "備註" FROM overdue_work_orders ORDER BY rowid'
        ).fetchall()
    assert notes == [("",), ("",)]


def test_export_preserves_all_columns_text_style_and_taipei_filename(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    records = [
        {field: f"{prefix}{index}" for index, field in enumerate(FIELDS)}
        for prefix in ("=", "+", "-", "@")
    ]
    replace_records(records, path)
    note = "=子工單(工單退回)\n第二筆"
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE overdue_work_orders SET "備註" = ? WHERE rowid = 1', (note,))
    now = datetime(2026, 11, 4, 18, 30, tzinfo=timezone.utc)
    first = tool.export_snapshot_xlsx(path, 4, output_directory=tmp_path, now=now)
    first_path = Path(first["output_file"])
    first_bytes = first_path.read_bytes()
    second = tool.export_snapshot_xlsx(path, 4, output_directory=tmp_path, now=now)
    assert first_path.name == "工單逾期查詢_程式產生1105.xlsx"
    assert Path(second["output_file"]).name == "工單逾期查詢_程式產生1105_2.xlsx"
    assert first_path.read_bytes() == first_bytes
    assert first["records_exported"] == 4
    assert first["columns_exported"] == 9
    workbook = load_workbook(first_path, data_only=False)
    try:
        sheet = workbook.active
        assert sheet.title == "工單逾期查詢"
        assert sheet.max_row == 5
        assert sheet.max_column == 9
        assert tuple(cell.value for cell in sheet[1]) == tool.DATABASE_FIELDS
        for row_number, record_index in enumerate((1, 2, 0, 3), start=2):
            record = records[record_index]
            expected = tuple(record[field] for field in FIELDS) + (
                note if record_index == 0 else None,
            )
            assert tuple(cell.value for cell in sheet[row_number]) == expected
            for cell in sheet[row_number]:
                assert cell.font.name == "微軟正黑體"
                assert cell.font.sz == 12
                assert not cell.font.bold
                assert cell.alignment.horizontal == "left"
                assert cell.alignment.vertical == "center"
                if cell.value is not None:
                    assert cell.data_type == "s"
                    assert cell.number_format == "@"
        assert sheet["I2"].alignment.wrap_text
        for cell in sheet[1]:
            assert cell.font.name == "微軟正黑體"
            assert cell.font.sz == 12
            assert cell.font.bold
            assert cell.alignment.horizontal == "center"
            assert cell.alignment.vertical == "center"
    finally:
        workbook.close()


@pytest.mark.parametrize("empty", [False, True])
def test_export_has_fixed_dimensions_even_with_multiline_notes(
    tmp_path: Path, empty: bool,
) -> None:
    path = tmp_path / "overdue.db"
    record = {field: "value" for field in FIELDS}
    replace_records([] if empty else [record], path)
    if not empty:
        with sqlite3.connect(path) as connection:
            connection.execute(
                'UPDATE overdue_work_orders SET "備註" = ?', ("第一行\n第二行\n第三行",)
            )
    result = tool.export_snapshot_xlsx(path, 0 if empty else 1, output_directory=tmp_path)
    workbook = load_workbook(result["output_file"])
    try:
        sheet = workbook.active
        assert sheet.max_row == (1 if empty else 2)
        assert tuple(cell.value for cell in sheet[1]) == tool.DATABASE_FIELDS
        assert [sheet.column_dimensions[column].width for column in "ABCDEFGHI"] == [
            10.6, 10.6, 17.9, 15.8, 8.1, 14.5, 14.5, 10.6, 40,
        ]
        assert sheet.row_dimensions[1].height == 16
        for row_number in range(2, sheet.max_row + 1):
            assert sheet.row_dimensions[row_number].height == 15.5
        if not empty:
            assert sheet["I2"].value == "第一行\n第二行\n第三行"
            assert sheet["I2"].alignment.wrap_text
    finally:
        workbook.close()


def test_export_sorts_three_text_keys_without_reordering_sqlite(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    records = []
    for number, level, overdue, vehicle in (
        ("WO-1", "3A", "10", "A"),
        ("WO-2", "2A", "2", "A"),
        ("WO-3", "2A", "10", "B"),
        ("WO-4", "1A", "2", "Z"),
        ("WO-5", "2A", "10", "A"),
        ("WO-6", "2A", "10", "A"),
    ):
        record = {field: "value" for field in FIELDS}
        record.update({
            "工單編號": number, "檢修級別": level, "逾期天數": overdue, "車組(輛)": vehicle,
        })
        records.append(record)
    replace_records(records, path)
    database_before = path.read_bytes()
    result = tool.export_snapshot_xlsx(path, len(records), output_directory=tmp_path)
    workbook = load_workbook(result["output_file"])
    try:
        assert [row[2] for row in list(workbook.active.values)[1:]] == [
            "WO-4", "WO-5", "WO-6", "WO-3", "WO-2", "WO-1",
        ]
        assert all(
            workbook.active.row_dimensions[row_number].height == 15.5
            for row_number in range(2, 8)
        )
    finally:
        workbook.close()
    assert path.read_bytes() == database_before
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            'SELECT "工單編號" FROM overdue_work_orders ORDER BY rowid'
        ).fetchall() == [(record["工單編號"],) for record in records]


@pytest.mark.parametrize("args", [
    ["--unknown"], ["--export-xlsx", "--export-xlsx"], ["--export-xlsx", "extra"],
])
def test_invalid_arguments_fail_before_session_creation(
    args: list[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_config():
        pytest.fail("invalid arguments must not start a session")

    monkeypatch.setattr(tool.MMISConfig, "from_env", unexpected_config)
    with pytest.raises(MMISClientError, match="用法:.*--export-xlsx"):
        tool.execute(args)


def test_export_count_mismatch_leaves_snapshot_and_writes_no_file(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    replace_records([{field: "value" for field in FIELDS}], path)
    before = path.read_bytes()
    with pytest.raises(MMISClientError, match="筆數"):
        tool.export_snapshot_xlsx(path, 2, output_directory=tmp_path)
    assert path.read_bytes() == before
    assert list(tmp_path.glob("*.xlsx")) == []


@pytest.mark.parametrize("kind, error", [
    ("too_long", "長度上限"),
    ("control_character", "控制字元"),
])
def test_export_rejects_unrepresentable_text_without_leaking_it(
    tmp_path: Path, kind: str, error: str,
) -> None:
    note = "A" * 32768 if kind == "too_long" else "secret\x01value"
    path = tmp_path / "overdue.db"
    record = {field: "value" for field in FIELDS}
    replace_records([record], path)
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE overdue_work_orders SET "備註" = ?', (note,))
    with pytest.raises(MMISClientError, match=error) as failure:
        tool.export_snapshot_xlsx(path, 1, output_directory=tmp_path)
    assert "secret" not in str(failure.value)
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            'SELECT "備註" FROM overdue_work_orders'
        ).fetchone()[0] == note
    assert list(tmp_path.glob("*.xlsx")) == []


def test_export_failure_preserves_completed_annotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "overdue.db"
    record = {field: "value" for field in FIELDS}
    record.update({"工單編號": "WO-2A", "檢修級別": "2A"})

    class OverdueQuery:
        def __init__(self, session):
            pass

        def run(self):
            return [record]

    class StatusQuery:
        def __init__(self, session):
            pass

        def run(self, order):
            return {"records": [{"工作單": "CHILD", "工作單狀態": "工單退回"}]}

    monkeypatch.setattr(tool, "DATABASE_PATH", path)
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda config: object())
    monkeypatch.setattr(tool, "OverdueWorkOrderQuery", OverdueQuery)
    monkeypatch.setattr(tool, "CompletePeriodicInspectionWorkOrderStatusQuery", StatusQuery)
    monkeypatch.setenv("UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR", str(tmp_path / "missing"))
    assert tool.main(["--export-xlsx"]) == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            'SELECT "工單編號", "備註" FROM overdue_work_orders'
        ).fetchall() == [("WO-2A", "CHILD(工單退回)")]
    assert "Status: FAILED" in capsys.readouterr().out
    assert list(tmp_path.glob("*.xlsx")) == []
