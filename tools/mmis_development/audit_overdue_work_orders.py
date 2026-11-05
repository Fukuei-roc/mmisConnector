from __future__ import annotations

import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.overdue_work_orders import FIELDS, OverdueWorkOrderQuery

DATABASE_RELATIVE_PATH = Path("data/overdue_work_orders.db")
DATABASE_PATH = Path(__file__).resolve().parents[2] / DATABASE_RELATIVE_PATH
TABLE_NAME = "overdue_work_orders"
DATABASE_FIELDS = (*FIELDS, "備註")
USAGE = "python -m tools.mmis_development.audit_overdue_work_orders"


def replace_records(records: list[dict[str, str]], path: Path = DATABASE_PATH) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ", ".join(f'"{field}" TEXT NOT NULL' for field in FIELDS)
    names = ", ".join(f'"{field}"' for field in DATABASE_FIELDS)
    marks = ", ".join("?" for _ in DATABASE_FIELDS)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        connection.execute(
            f'''CREATE TABLE {TABLE_NAME} (
                {columns}, "備註" TEXT NOT NULL DEFAULT '',
                PRIMARY KEY ("工單編號")
            )'''
        )
        connection.executemany(
            f"INSERT INTO {TABLE_NAME} ({names}) VALUES ({marks})",
            (tuple(record[field] for field in FIELDS) + ("",) for record in records),
        )
        saved = connection.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        if saved != len(records):
            raise MMISClientError("逾期工單資料庫筆數不符")
        return saved


def execute(args: Sequence[str]) -> dict[str, str | int | bool]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    session = MMISSession(MMISConfig.from_env())
    records = OverdueWorkOrderQuery(session).run()
    return {
        "success": True,
        "count": replace_records(records),
        "database_path": DATABASE_RELATIVE_PATH.as_posix(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = execute(sys.argv[1:] if argv is None else argv)
    except Exception as exc:  # noqa: BLE001
        print("Status: FAILED")
        print(f"Database path: {DATABASE_RELATIVE_PATH.as_posix()}")
        print(f"Error: {type(exc).__name__}: {exc}")
        return 1
    print("Status: SUCCESS")
    print(f"Records found: {result['count']}")
    print(f"Database path: {result['database_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
