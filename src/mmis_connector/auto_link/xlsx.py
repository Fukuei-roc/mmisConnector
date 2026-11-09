"""Export the committed auto-link result table without opening an MMIS session."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from ..auth import MMISClientError
from .store import DEFAULT_DATABASE_PATH, RESULT_COLUMNS


OUTPUT_ENV = "UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR"
FILE_PREFIX = "未處理故障通報日檢勾稽_程式產生"
EXPORT_COLUMNS = RESULT_COLUMNS[1:]
COLUMN_WIDTHS = {
    "車次": 6.5,
    "車組/車號": 11.8,
    "發生日期": 14.5,
    "事故等級": 10.6,
    "ATP故障": 10.4,
    "故障現象": 73.6,
    "狀態": 5.7,
    "通報號": 14.9,
    "已關聯的工單": 17.9,
    "執行結果": 23.6,
}


def export_xlsx(
    database_path: Path = DEFAULT_DATABASE_PATH,
    *,
    output_directory: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Read the result snapshot and create a new XLSX file."""
    if output_directory is None:
        load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
        configured = os.getenv(OUTPUT_ENV, "").strip().strip('"\'')
        if not configured:
            raise MMISClientError(f"未設定 {OUTPUT_ENV}")
        output_directory = Path(configured).expanduser()
    if not output_directory.is_absolute() or not output_directory.is_dir():
        raise MMISClientError(f"{OUTPUT_ENV} 必須指向現有的絕對路徑資料夾")

    try:
        with closing(sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(fault_notices)"))
            if columns != RESULT_COLUMNS:
                raise MMISClientError("SQLite fault_notices 欄位與預期結果不符")
            rows = connection.execute('SELECT * FROM "fault_notices" ORDER BY rowid').fetchall()
    except sqlite3.Error as exc:
        raise MMISClientError(f"無法讀取 SQLite 結果表: {type(exc).__name__}") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "未處理故障通報日檢勾稽"
    sheet.append(EXPORT_COLUMNS)
    header_font = Font(name="微軟正黑體", size=12, bold=True)
    data_font = Font(name="微軟正黑體", size=12)
    for cell in sheet[1]:
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[1].height = 16

    for row_number, row in enumerate(rows, start=2):
        for index, value in enumerate(row[1:], start=1):
            if EXPORT_COLUMNS[index - 1] == "ATP故障" and isinstance(value, str):
                value = {"true": "Y", "false": "N"}.get(value.lower(), value)
            cell = sheet.cell(row_number, index)
            cell.value = value
            if isinstance(value, str):
                cell.data_type = "s"
                cell.number_format = "@"
            cell.font = data_font
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        sheet.row_dimensions[row_number].height = 15.5
    for index, name in enumerate(EXPORT_COLUMNS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = COLUMN_WIDTHS[name]

    date = (now or datetime.now(ZoneInfo("Asia/Taipei"))).astimezone(
        ZoneInfo("Asia/Taipei")
    ).strftime("%m%d")
    base = f"{FILE_PREFIX}{date}"
    output_file = None
    saved = False
    try:
        suffix = 1
        while True:
            name = f"{base}{'_' + str(suffix) if suffix > 1 else ''}.xlsx"
            output_file = output_directory / name
            try:
                handle = output_file.open("xb")
                break
            except FileExistsError:
                suffix += 1
        with handle:
            workbook.save(handle)
        saved = True
    except OSError as exc:
        raise MMISClientError(f"XLSX 寫入失敗: {type(exc).__name__}") from exc
    finally:
        workbook.close()
        if output_file is not None and not saved:
            output_file.unlink(missing_ok=True)
    return {"status": "success", "records_exported": len(rows),
            "columns_exported": len(EXPORT_COLUMNS), "output_file": str(output_file)}
