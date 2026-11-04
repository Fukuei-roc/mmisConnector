"""Collect the unassigned 1A work orders for a later duplicate review step."""
from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.unassigned import FIELDS, UnassignedDailyInspectionWorkOrderQuery

DATABASE_RELATIVE_PATH = Path("data/auto_delete_duplicate_daily_inspection_work_orders.db")
DATABASE_PATH = Path(__file__).resolve().parents[2] / DATABASE_RELATIVE_PATH
TABLE = "daily_inspection_work_orders"


def replace_records(records: list[dict[str, str]], path: Path = DATABASE_PATH) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    queried_at = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f'DROP TABLE IF EXISTS {TABLE}')
        connection.execute(f'''CREATE TABLE {TABLE} (
            "車組/車號" TEXT NOT NULL,
            "工作單" TEXT NOT NULL PRIMARY KEY,
            "預計檢修(進廠)日" TEXT NOT NULL,
            "查詢時間" TEXT NOT NULL,
            "執行結果" TEXT NOT NULL
        )''')
        connection.executemany(
            f'INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?)',
            ((record[FIELDS[0]], record[FIELDS[1]], record[FIELDS[2]], queried_at, "")
             for record in records),
        )
        count = connection.execute(f'SELECT COUNT(*) FROM {TABLE}').fetchone()[0]
        if count != len(records):
            raise MMISClientError("未派工日檢工單寫入筆數不符")
        return count


def main(argv: list[str] | None = None) -> int:
    if (sys.argv[1:] if argv is None else argv):
        print("Error: this command accepts no arguments", file=sys.stderr)
        return 2
    try:
        records = UnassignedDailyInspectionWorkOrderQuery(MMISSession(MMISConfig.from_env())).run()
        count = replace_records(records)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"Records found: {count}")
    print(f"Database path: {DATABASE_RELATIVE_PATH.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
