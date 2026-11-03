from __future__ import annotations

import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.not_submitted import (
    DailyInspectionNotSubmittedQuery,
    FIELDS,
)
from mmis_connector.daily_inspection.reader import DailyInspectionInspectionRecordReader

from .query_daily_inspection_work_order_details import group_maintenance_personnel

DATABASE_RELATIVE_PATH = Path("data/daily_inspection_work_orders_not_submitted_for_approval.db")
DATABASE_PATH = Path(__file__).resolve().parents[2] / DATABASE_RELATIVE_PATH
TABLE_NAME = "daily_inspection_work_orders_not_submitted_for_approval"
NOTIFICATION_NOTE = "通知檢車室"
DATABASE_FIELDS = (*FIELDS, "備註欄")
FIELD_NAMES_SQL = ", ".join(f'"{field}"' for field in DATABASE_FIELDS)
CREATE_TABLE_SQL = f'''CREATE TABLE {TABLE_NAME} (
    {", ".join(f'"{field}" TEXT' for field in FIELDS[:-1])},
    "{FIELDS[-1]}" INTEGER NOT NULL CHECK ("{FIELDS[-1]}" IN (0, 1)),
    "備註欄" TEXT NOT NULL DEFAULT '',
    PRIMARY KEY ("工作單")
)'''
INSERT_SQL = (
    f'INSERT INTO {TABLE_NAME} '
    f'({FIELD_NAMES_SQL}) '
    f'VALUES ({", ".join("?" for _ in DATABASE_FIELDS)})'
)
XLSX_COLUMNS = ("項次", "車組/車號", "工作單", "車次", "檢修日期")
XLSX_WIDTHS = dict(zip(XLSX_COLUMNS, (5.7, 11.8, 17.9, 6.5, 14.5), strict=True))
USAGE = (
    "python -m tools.mmis_development."
    "query_daily_inspection_work_orders_not_submitted_for_approval [--export-xlsx]"
)


def replace_records(records: list[dict[str, Any]], database_path: Path | None = None) -> int:
    path = database_path or DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        connection.execute(CREATE_TABLE_SQL)
        connection.executemany(
            INSERT_SQL,
            (
                tuple(record[field] for field in FIELDS[:-1])
                + (int(record[FIELDS[-1]]), "")
                for record in records
            ),
        )
        saved = connection.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        if saved != len(records):
            raise MMISClientError("未送簽核日檢工單寫入筆數不符")
        return saved


def mark_orders_requiring_personnel(
    database_path: Path, reader: DailyInspectionInspectionRecordReader,
) -> int:
    with closing(sqlite3.connect(database_path)) as connection:
        work_orders = [
            row[0] for row in connection.execute(
                f'SELECT "工作單" FROM {TABLE_NAME} '
                'WHERE "工作單狀態" = ? ORDER BY rowid',
                ("執行中已派工",),
            )
        ]
        requiring_notice = []
        for work_order in work_orders:
            detail = reader.run(work_order)
            if detail["work_order"] != work_order or detail["success"] is not True:
                raise MMISClientError(f"日檢工單明細與快照不符: {work_order}")
            personnel = group_maintenance_personnel(detail["maintenance_personnel"])
            if (
                detail["maintenance_records_complete"] is True
                and personnel["檢車室（檢查員）"]["records"] == []
                and personnel["檢車室（技術人員）"]["records"] == []
            ):
                requiring_notice.append((NOTIFICATION_NOTE, work_order))

        with connection:
            connection.executemany(
                f'UPDATE {TABLE_NAME} SET "備註欄" = ? WHERE "工作單" = ?',
                requiring_notice,
            )
        return connection.execute(
            f'SELECT COUNT(*) FROM {TABLE_NAME} WHERE "備註欄" = ?',
            (NOTIFICATION_NOTE,),
        ).fetchone()[0]


def export_snapshot_xlsx(
    database_path: Path, expected_records: int, *,
    output_directory: Path | None = None, now: datetime | None = None,
) -> dict[str, Any]:
    try:
        from ._unclosed_ab_xlsx import (
            XlsxExportError, build_workbook, configured_output_directory,
            read_snapshot, save_workbook,
        )
    except ModuleNotFoundError as exc:
        if exc.name == "openpyxl":
            raise MMISClientError("未安裝 openpyxl，無法匯出 XLSX") from exc
        raise

    directory = output_directory if output_directory is not None else configured_output_directory()
    if not directory.is_dir():
        raise XlsxExportError("XLSX 輸出資料夾不存在")
    rows = read_snapshot(database_path, TABLE_NAME, DATABASE_FIELDS)
    if len(rows) != expected_records:
        raise XlsxExportError("本次 SQLite 筆數與 XLSX 匯出筆數不符")
    indices = tuple(FIELDS.index(name) for name in XLSX_COLUMNS[1:])
    note_index = DATABASE_FIELDS.index("備註欄")
    projected = [
        tuple(row[index] for index in indices)
        for row in rows if row[note_index] == NOTIFICATION_NOTE
    ]
    projected.sort(
        key=lambda row: tuple(str(row[index] or "").casefold() for index in (3, 2, 0))
    )
    numbered = [(number, *row) for number, row in enumerate(projected, start=1)]
    workbook = build_workbook(
        numbered, XLSX_COLUMNS, frozenset(),
        row_height=15.5, column_widths=XLSX_WIDTHS,
    )
    workbook.active.title = "未填檢修人員日檢工單"
    return save_workbook(
        workbook, directory, file_prefix="檢車室未填檢修人員日檢工單_程式產生",
        records_exported=len(projected), columns_exported=len(XLSX_COLUMNS), now=now,
    )


def execute(args: Sequence[str]) -> dict[str, Any]:
    if list(args) not in ([], ["--export-xlsx"]):
        raise MMISClientError(f"用法: {USAGE}")
    session = MMISSession(MMISConfig.from_env())
    result = DailyInspectionNotSubmittedQuery(session).run()
    count = replace_records(result["records"])
    notification_count = mark_orders_requiring_personnel(
        DATABASE_PATH, DailyInspectionInspectionRecordReader(session)
    )
    output = {
        "success": True,
        "count": count,
        "notification_count": notification_count,
        "database_path": DATABASE_RELATIVE_PATH.as_posix(),
    }
    if args:
        output["xlsx_export"] = export_snapshot_xlsx(DATABASE_PATH, count)
    return output


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = execute(sys.argv[1:] if argv is None else argv)
    except Exception as exc:  # noqa: BLE001
        print("Status: FAILED")
        print("Records found: unavailable")
        print(f"Database path: {DATABASE_RELATIVE_PATH.as_posix()}")
        print(f"Error: {type(exc).__name__}")
        return 1
    print("Status: SUCCESS")
    print(f"Records found: {result['count']}")
    print(f"Vehicle room notifications: {result['notification_count']}")
    print(f"Database path: {result['database_path']}")
    if "xlsx_export" in result:
        print(f"Excel path: {result['xlsx_export']['output_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
