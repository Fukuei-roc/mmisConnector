from datetime import datetime
from zoneinfo import ZoneInfo

from openpyxl import load_workbook

from mmis_connector.auto_link.store import AutoLinkStore
from mmis_connector.auto_link.xlsx import COLUMN_WIDTHS, EXPORT_COLUMNS, export_xlsx


def test_export_existing_result_table_without_changing_database(tmp_path):
    database = tmp_path / "snapshot.sqlite3"
    with AutoLinkStore(database) as store:
        store.connection.execute(
            'INSERT INTO fault_notices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            ("2026-11-09T10:00:00+08:00", "=123", "EP9393", "2026/11/08", "B",
             "true", "故障\n現象", "未處理", "F123", None, "未執行"),
        )
        store.connection.execute(
            'INSERT INTO fault_notices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            ("2026-11-09T11:00:00+08:00", "456", "EP9394", "2026/11/09", "A",
             "false", "其他故障", "未處理", "F124", "WO456", "是"),
        )
        store.connection.commit()
    before = database.read_bytes()

    result = export_xlsx(database, output_directory=tmp_path,
                         now=datetime(2026, 11, 9, tzinfo=ZoneInfo("Asia/Taipei")))

    assert database.read_bytes() == before
    assert result["records_exported"] == 2
    assert result["columns_exported"] == 10
    assert result["output_file"].endswith("未處理故障通報日檢勾稽_程式產生1109.xlsx")
    workbook = load_workbook(result["output_file"])
    sheet = workbook.active
    assert tuple(cell.value for cell in sheet[1]) == EXPORT_COLUMNS
    assert tuple(cell.value for cell in sheet[2]) == (
        "=123", "EP9393", "2026/11/08", "B", "Y",
        "故障\n現象", "未處理", "F123", None, "未執行",
    )
    assert sheet["E3"].value == "N"
    assert sheet["A2"].data_type == "s"
    assert sheet["A2"].font.name == "微軟正黑體"
    assert sheet["A2"].alignment.horizontal == "left"
    assert sheet["A1"].alignment.horizontal == "center"
    assert sheet.row_dimensions[1].height == 16
    assert sheet.row_dimensions[2].height == 15.5
    assert sheet.row_dimensions[3].height == 15.5
    for index, name in enumerate(EXPORT_COLUMNS, start=1):
        assert sheet.column_dimensions[sheet.cell(1, index).column_letter].width == COLUMN_WIDTHS[name]
    workbook.close()
