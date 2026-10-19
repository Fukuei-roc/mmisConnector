"""Snapshot A/B unclosed fault notices into a local development SQLite database."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.query import (
    UNCLOSED_DEPOT_NAME,
    UNCLOSED_INCIDENT_LEVELS,
    UNCLOSED_QUERY_NAME,
    UnclosedFaultNoticeQuery,
)


USAGE = "python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices"
DATABASE_RELATIVE_PATH = Path("data/unclosed_ab_fault_notices.db")
DATABASE_PATH = Path(__file__).resolve().parents[2] / DATABASE_RELATIVE_PATH
TABLE_NAME = "unclosed_ab_fault_notices"
BASIC_FIELDS = (
    "車次", "車組/車號", "發生日期", "事故等級", "ATP故障",
    "故障現象", "狀態", "通報號",
)
RESERVED_FIELDS = (
    "Sufficient Data for Fault Analysis",
    "Fault Analysis Completed",
    "All Depot Maintenance Work Orders Closed",
    "Depot Maintenance Work Orders Pending Approval",
    "CA Repair Work Orders Not Closed",
    "ATP Fault Analysis Incomplete",
    "備註",
)
COLUMNS = (
    ("車次", "TEXT", 0, 0),
    ("車組/車號", "TEXT", 0, 0),
    ("發生日期", "TEXT", 0, 0),
    ("事故等級", "TEXT", 0, 0),
    ("ATP故障", "INTEGER", 0, 0),
    ("故障現象", "TEXT", 0, 0),
    ("狀態", "TEXT", 0, 0),
    ("通報號", "TEXT", 1, 1),
    *((name, "INTEGER", 0, 0) for name in RESERVED_FIELDS[:-1]),
    ("備註", "TEXT", 0, 0),
)
CREATE_TABLE_SQL = '''
CREATE TABLE unclosed_ab_fault_notices (
    "車次" TEXT,
    "車組/車號" TEXT,
    "發生日期" TEXT,
    "事故等級" TEXT,
    "ATP故障" INTEGER,
    "故障現象" TEXT,
    "狀態" TEXT,
    "通報號" TEXT PRIMARY KEY NOT NULL,
    "Sufficient Data for Fault Analysis" INTEGER DEFAULT NULL,
    "Fault Analysis Completed" INTEGER DEFAULT NULL,
    "All Depot Maintenance Work Orders Closed" INTEGER DEFAULT NULL,
    "Depot Maintenance Work Orders Pending Approval" INTEGER DEFAULT NULL,
    "CA Repair Work Orders Not Closed" INTEGER DEFAULT NULL,
    "ATP Fault Analysis Incomplete" INTEGER DEFAULT NULL,
    "備註" TEXT DEFAULT NULL
)
'''
INSERT_SQL = '''
INSERT INTO unclosed_ab_fault_notices
("車次", "車組/車號", "發生日期", "事故等級", "ATP故障",
 "故障現象", "狀態", "通報號")
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
'''


@dataclass
class SyncState:
    transaction_started: bool = False
    rolled_back: bool = False
    old_data_unchanged: bool = True


def fetch_unclosed_fault_notices() -> dict[str, Any]:
    client = MMISSession(MMISConfig.from_env())
    client.login()
    return UnclosedFaultNoticeQuery(client).run()


def prepare_rows(result: dict[str, Any]) -> list[tuple[Any, ...]]:
    """Accept only a complete result from the fixed unclosed A/B query."""
    if not isinstance(result, dict) or result.get("success") is not True:
        raise MMISClientError("未結案故障通報查詢未確認成功")
    if result.get("query_name") != UNCLOSED_QUERY_NAME or result.get("filters") != {
        "配屬段別名稱": UNCLOSED_DEPOT_NAME,
        "事故等級": UNCLOSED_INCIDENT_LEVELS,
    }:
        raise MMISClientError("未結案故障通報查詢條件不符")
    records = result.get("records")
    count = result.get("count")
    if (not isinstance(records, list) or type(count) is not int
            or count != len(records)):
        raise MMISClientError("未結案故障通報查詢筆數不完整")

    rows: list[tuple[Any, ...]] = []
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict) or any(field not in record for field in BASIC_FIELDS):
            raise MMISClientError(f"第 {index} 筆故障通報缺少基本欄位")
        number = record["通報號"]
        if not isinstance(number, str) or not number.strip():
            raise MMISClientError(f"第 {index} 筆故障通報缺少通報號")
        if number in seen:
            raise MMISClientError(f"第 {index} 筆故障通報的通報號重複")
        seen.add(number)
        if record["事故等級"] not in ("A", "B"):
            raise MMISClientError(f"第 {index} 筆故障通報不是 A/B 級")
        for field in BASIC_FIELDS:
            if field == "ATP故障":
                if record[field] is not None and type(record[field]) is not bool:
                    raise MMISClientError(f"第 {index} 筆故障通報的 ATP故障 型別錯誤")
            elif record[field] is not None and not isinstance(record[field], str):
                raise MMISClientError(f"第 {index} 筆故障通報的 {field} 型別錯誤")
        if not isinstance(record["狀態"], str) or not record["狀態"].strip():
            raise MMISClientError(f"第 {index} 筆故障通報缺少狀態")
        rows.append(tuple(
            int(record[field]) if field == "ATP故障" and record[field] is not None
            else record[field]
            for field in BASIC_FIELDS
        ))
    return rows


def _check_schema(connection: sqlite3.Connection) -> None:
    actual = connection.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()
    if len(actual) != len(COLUMNS):
        raise MMISClientError("既有故障通報資料表 schema 不符")
    for column, expected in zip(actual, COLUMNS, strict=True):
        _, name, kind, not_null, default, primary_key = column
        if ((name, kind.upper(), not_null, primary_key) != expected
                or (default is not None and str(default).upper() != "NULL")):
            raise MMISClientError("既有故障通報資料表 schema 不符")


def replace_rows(
    rows: list[tuple[Any, ...]], database_path: Path, state: SyncState
) -> int:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        state.transaction_started = True
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (TABLE_NAME,),
        ).fetchone()
        if exists is None:
            connection.execute(CREATE_TABLE_SQL)
        _check_schema(connection)
        connection.execute(f"DELETE FROM {TABLE_NAME}")
        connection.executemany(INSERT_SQL, rows)
        saved = connection.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        if saved != len(rows):
            raise MMISClientError("故障通報寫入筆數不符")
        reserved_not_null = " OR ".join(f'"{field}" IS NOT NULL' for field in RESERVED_FIELDS)
        if connection.execute(
            f"SELECT 1 FROM {TABLE_NAME} WHERE {reserved_not_null} LIMIT 1"
        ).fetchone():
            raise MMISClientError("故障通報預留欄位未保持 NULL")
        connection.commit()
        state.old_data_unchanged = False
        return saved
    except Exception:
        if state.transaction_started:
            try:
                connection.rollback()
                state.rolled_back = True
            except sqlite3.Error:
                state.old_data_unchanged = False
        raise
    finally:
        connection.close()


def execute(
    args: Sequence[str], *, database_path: Path | None = None,
    state: SyncState | None = None,
) -> dict[str, Any]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    state = state if state is not None else SyncState()
    rows = prepare_rows(fetch_unclosed_fault_notices())
    saved = replace_rows(rows, database_path or DATABASE_PATH, state)
    return {
        "success": True,
        "status": "success",
        "database": str(DATABASE_RELATIVE_PATH).replace("\\", "/"),
        "table": TABLE_NAME,
        "records_fetched": len(rows),
        "records_saved": saved,
        "sync_mode": "full_replace",
    }


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    state = SyncState()
    try:
        result = execute(list(sys.argv[1:] if argv is None else argv), state=state)
    except Exception as exc:  # noqa: BLE001
        message = (str(exc) if isinstance(exc, MMISClientError)
                   else "發生未預期錯誤；已隱藏詳細內容以避免洩漏敏感資料")
        result = {
            "success": False,
            "status": "failed",
            "error": type(exc).__name__,
            "message": message,
            "transaction_started": state.transaction_started,
            "rolled_back": state.rolled_back,
            "old_data_unchanged": state.old_data_unchanged,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
