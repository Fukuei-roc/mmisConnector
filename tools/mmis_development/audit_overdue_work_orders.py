from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.overdue_work_orders import FIELDS, OverdueWorkOrderQuery
from mmis_connector.periodic_inspection.status import (
    CompletePeriodicInspectionWorkOrderStatusQuery,
)

DATABASE_RELATIVE_PATH = Path("data/overdue_work_orders.db")
DATABASE_PATH = Path(__file__).resolve().parents[2] / DATABASE_RELATIVE_PATH
TABLE_NAME = "overdue_work_orders"
DATABASE_FIELDS = (*FIELDS, "備註")
USAGE = "python -m tools.mmis_development.audit_overdue_work_orders"
EXCLUDED_STATUSES = {"核簽中", "工單結案"}
PERIODIC_LEVELS = ("2A", "3A")


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


def annotate_periodic_records(
    query: CompletePeriodicInspectionWorkOrderStatusQuery,
    path: Path = DATABASE_PATH,
) -> list[dict[str, str]]:
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        orders = connection.execute(
            f'SELECT "工單編號" FROM {TABLE_NAME} '
            'WHERE "檢修級別" IN (?, ?) ORDER BY rowid',
            PERIODIC_LEVELS,
        ).fetchall()
        notes: list[tuple[str, str]] = []
        for row in orders:
            order = row["工單編號"]
            children = query.run(order)["records"]
            note = ",".join(
                f'{child["工作單"]}({child["工作單狀態"]})'
                for child in children
                if child["工作單狀態"] not in EXCLUDED_STATUSES
            )
            if note:
                notes.append((note, order))
        with connection:
            connection.executemany(
                f'UPDATE {TABLE_NAME} SET "備註" = ? WHERE "工單編號" = ?',
                notes,
            )
        return [
            dict(row)
            for row in connection.execute(
                f'SELECT * FROM {TABLE_NAME} WHERE "備註" <> ? ORDER BY rowid',
                ("",),
            )
        ]


def execute(args: Sequence[str]) -> dict[str, str | int | bool | list[dict[str, str]]]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    session = MMISSession(MMISConfig.from_env())
    records = OverdueWorkOrderQuery(session).run()
    count = replace_records(records, DATABASE_PATH)
    noted_records = annotate_periodic_records(
        CompletePeriodicInspectionWorkOrderStatusQuery(session), DATABASE_PATH
    )
    return {
        "success": True,
        "count": count,
        "database_path": DATABASE_RELATIVE_PATH.as_posix(),
        "noted_records": noted_records,
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
    print(json.dumps(result["noted_records"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
