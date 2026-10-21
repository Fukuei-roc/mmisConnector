"""Snapshot A/B unclosed fault notices into a local development SQLite database."""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.query import (
    UNCLOSED_DEPOT_NAME,
    UNCLOSED_INCIDENT_LEVELS,
    UNCLOSED_QUERY_NAME,
    UnclosedFaultNoticeQuery,
)
from mmis_connector.fault_notices.analysis_readiness import AnalysisEvidenceIncomplete
from mmis_connector.fault_notices.analysis_writer import (
    FaultNoticeAnalysisWriter, WRITE_FIELDS,
)

from . import query_fault_notice_full_detail


USAGE = (
    "python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices "
    "[--check-analysis-readiness] [--export-xlsx]"
)
DATABASE_RELATIVE_PATH = Path("data/unclosed_ab_fault_notices.db")
DATABASE_PATH = Path(__file__).resolve().parents[2] / DATABASE_RELATIVE_PATH
TABLE_NAME = "unclosed_ab_fault_notices"
WAITING_DATABASE_NAME = "a_level_fault_notices_awaiting_closure.db"
WAITING_DATABASE_RELATIVE_PATH = Path("data") / WAITING_DATABASE_NAME
WAITING_TABLE_NAME = "a_level_fault_notices_awaiting_closure"
WAITING_RECHECK_VERSION = 1
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
DETAIL_CHECK_FIELDS = RESERVED_FIELDS[:-1]
DETAIL_CHECK_SELECT = ", ".join(f'"{field}"' for field in DETAIL_CHECK_FIELDS)
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
CREATE_WAITING_TABLE_SQL = '''
CREATE TABLE a_level_fault_notices_awaiting_closure (
    "通報號" TEXT PRIMARY KEY NOT NULL,
    "新增日期" TEXT NOT NULL
)
'''
WAITING_COLUMNS = (
    ("通報號", "TEXT", 1, 1),
    ("新增日期", "TEXT", 1, 0),
)


@dataclass
class SyncState:
    transaction_started: bool = False
    rolled_back: bool = False
    old_data_unchanged: bool = True
    snapshot_saved: bool = False
    detail_transaction_started: bool = False
    detail_rolled_back: bool = False
    detail_updated: bool = False
    details_processed: int = 0
    readiness_queries: int = 0
    readiness_saved: int = 0
    readiness_unresolved: list[dict[str, str]] = field(default_factory=list)
    waiting_transaction_started: bool = False
    waiting_rolled_back: bool = False
    waiting_added: int = 0
    records_fetched: int = 0
    records_skipped_waiting: int = 0
    records_loaded: int = 0
    waiting_rechecked: bool = False
    export_requested: bool = False
    sync_completed: bool = False
    analysis_target: str | None = None
    analysis_written: int = 0


def fetch_unclosed_fault_notices() -> dict[str, Any]:
    client = MMISSession(MMISConfig.from_env())
    client.login()
    return UnclosedFaultNoticeQuery(client).run()


def fetch_fault_notice_detail(
    notice_number: str, *, check_analysis_readiness: bool
) -> dict[str, Any]:
    args = [notice_number]
    if check_analysis_readiness:
        args.append("--check-analysis-readiness")
    for attempt in range(3):
        try:
            return query_fault_notice_full_detail.execute(
                args, include_analysis_materials=check_analysis_readiness
            )
        except AnalysisEvidenceIncomplete:
            raise
        except Exception:
            if attempt == 2:
                raise
            if attempt == 1:
                time.sleep(1)
    raise AssertionError("unreachable")


def prepare_detail_checks(
    detail: dict[str, Any], notice_number: str, *, require_readiness: bool
) -> tuple[int | None, ...]:
    if not isinstance(detail, dict) or detail.get("通報號") != notice_number:
        raise MMISClientError("完整通報查詢回傳的通報號不符")
    checks = detail.get("結案狀態檢查")
    if not isinstance(checks, dict) or any(
        field not in checks for field in DETAIL_CHECK_FIELDS
    ):
        raise MMISClientError("完整通報查詢缺少結案狀態檢查欄位")
    values: list[int | None] = []
    for field in DETAIL_CHECK_FIELDS:
        value = checks[field]
        if field == DETAIL_CHECK_FIELDS[0] and not require_readiness:
            if value is not None:
                raise MMISClientError(f"完整通報查詢的 {field} 型別錯誤")
            values.append(None)
        elif type(value) is bool:
            values.append(int(value))
        else:
            raise MMISClientError(f"完整通報查詢的 {field} 型別錯誤")
    return tuple(values)


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


def _check_waiting_schema(connection: sqlite3.Connection, database: str = "main") -> None:
    actual = connection.execute(
        f"PRAGMA {database}.table_info({WAITING_TABLE_NAME})"
    ).fetchall()
    if len(actual) != len(WAITING_COLUMNS):
        raise MMISClientError("既有等候結案資料表 schema 不符")
    for column, expected in zip(actual, WAITING_COLUMNS, strict=True):
        _, name, kind, not_null, default, primary_key = column
        if ((name, kind.upper(), not_null, primary_key) != expected
                or default is not None):
            raise MMISClientError("既有等候結案資料表 schema 不符")


def load_waiting_notice_numbers(database_path: Path) -> set[str]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (WAITING_TABLE_NAME,),
        ).fetchone()
        if exists is None:
            connection.execute(CREATE_WAITING_TABLE_SQL)
            connection.execute(f"PRAGMA user_version = {WAITING_RECHECK_VERSION}")
        _check_waiting_schema(connection)
        numbers = {
            row[0] for row in connection.execute(
                f'SELECT "通報號" FROM {WAITING_TABLE_NAME}'
            )
        }
        connection.commit()
        return numbers
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def waiting_recheck_pending(database_path: Path) -> bool:
    connection = sqlite3.connect(database_path)
    try:
        _check_waiting_schema(connection)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        return version < WAITING_RECHECK_VERSION
    finally:
        connection.close()


def is_awaiting_closure(incident_level: str, checks: tuple[int | None, ...]) -> bool:
    return incident_level == "A" and checks[1:] == (1, 1, 0, 0, 0)


def current_added_at() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")


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
    rows: list[tuple[Any, ...]], database_path: Path, state: SyncState,
    *, waiting_database_path: Path | None = None,
) -> int:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        if waiting_database_path is not None:
            connection.execute("ATTACH DATABASE ? AS waiting", (str(waiting_database_path),))
            if any(
                connection.execute(f"PRAGMA {name}.journal_mode").fetchone()[0].lower() == "wal"
                for name in ("main", "waiting")
            ):
                raise MMISClientError("重新清查需要兩個資料庫使用非 WAL journal mode")
        connection.execute("BEGIN IMMEDIATE")
        state.transaction_started = True
        if waiting_database_path is not None:
            _check_waiting_schema(connection, "waiting")
            version = connection.execute("PRAGMA waiting.user_version").fetchone()[0]
            if version >= WAITING_RECHECK_VERSION:
                raise MMISClientError("等候結案資料庫已完成重新清查，請重新執行")
            connection.execute(f"DELETE FROM waiting.{WAITING_TABLE_NAME}")
            connection.execute(f"PRAGMA waiting.user_version = {WAITING_RECHECK_VERSION}")
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
        reserved_not_null = " OR ".join(f'"{field}" IS NOT NULL' for field in DETAIL_CHECK_FIELDS)
        if connection.execute(
            f"SELECT 1 FROM {TABLE_NAME} WHERE {reserved_not_null} LIMIT 1"
        ).fetchone():
            raise MMISClientError("故障通報預留欄位未保持 NULL")
        if connection.execute(
            f'SELECT 1 FROM {TABLE_NAME} WHERE "備註" IS NOT NULL LIMIT 1'
        ).fetchone():
            raise MMISClientError("故障通報預留欄位備註未重置")
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


def update_detail_checks(
    notice_number: str,
    checks: tuple[int | None, ...],
    database_path: Path,
    state: SyncState,
) -> None:
    assignments = ", ".join(f'"{field}" = ?' for field in DETAIL_CHECK_FIELDS)
    selected = ", ".join(f'"{field}"' for field in DETAIL_CHECK_FIELDS)
    connection = sqlite3.connect(database_path)
    transaction_started = False
    try:
        connection.execute("BEGIN IMMEDIATE")
        transaction_started = True
        state.detail_transaction_started = True
        _check_schema(connection)
        cursor = connection.execute(
            f'UPDATE {TABLE_NAME} SET {assignments} WHERE "通報號" = ?',
            (*checks, notice_number),
        )
        if cursor.rowcount != 1:
            raise MMISClientError("完整通報檢查值未更新唯一通報")
        stored = connection.execute(
            f'SELECT {selected} FROM {TABLE_NAME} WHERE "通報號" = ?',
            (notice_number,),
        ).fetchone()
        if stored != checks:
            raise MMISClientError("完整通報檢查值寫入驗證失敗")
        connection.commit()
        state.detail_updated = True
    except Exception:
        if transaction_started:
            try:
                connection.rollback()
                state.detail_rolled_back = True
            except sqlite3.Error:
                pass
        raise
    finally:
        connection.close()


def update_analysis_readiness(
    notice_number: str, readiness: int, database_path: Path, state: SyncState,
) -> None:
    connection = sqlite3.connect(database_path)
    transaction_started = False
    try:
        connection.execute("BEGIN IMMEDIATE")
        transaction_started = True
        state.detail_transaction_started = True
        _check_schema(connection)
        cursor = connection.execute(
            f'UPDATE {TABLE_NAME} SET "Sufficient Data for Fault Analysis" = ? '
            'WHERE "通報號" = ? AND "Fault Analysis Completed" = 0',
            (readiness, notice_number),
        )
        if cursor.rowcount != 1:
            raise MMISClientError("資料充分性未更新唯一且故障分析未完成的通報")
        stored = connection.execute(
            f'SELECT "Sufficient Data for Fault Analysis" FROM {TABLE_NAME} '
            'WHERE "通報號" = ?', (notice_number,),
        ).fetchone()
        if stored != (readiness,):
            raise MMISClientError("資料充分性寫入驗證失敗")
        connection.commit()
        state.readiness_saved += 1
    except Exception:
        if transaction_started:
            try:
                connection.rollback()
                state.detail_rolled_back = True
            except sqlite3.Error:
                pass
        raise
    finally:
        connection.close()


def pending_analysis_numbers(database_path: Path) -> list[str]:
    with sqlite3.connect(database_path) as connection:
        _check_schema(connection)
        return [row[0] for row in connection.execute(
            f'SELECT "通報號" FROM {TABLE_NAME} '
            'WHERE "Sufficient Data for Fault Analysis" = 1 '
            'AND "Fault Analysis Completed" = 0 AND "備註" IS NULL '
            'ORDER BY rowid'
        )]


def fetch_ai_analysis(notice_number: str) -> dict[str, str]:
    detail = query_fault_notice_full_detail.execute([notice_number, "--ai-analysis"])
    if detail.get("通報號") != notice_number:
        raise MMISClientError("AI 故障分析通報號不符")
    if detail.get("結案狀態檢查", {}).get("Fault Analysis Completed") is not False:
        raise MMISClientError("MMIS 故障分析狀態已變更，停止寫入")
    analysis = detail.get("故障分析")
    if not isinstance(analysis, dict) or any(
        not isinstance(analysis.get(field), str) or not analysis[field].strip()
        for field in WRITE_FIELDS
    ):
        raise MMISClientError("AI 故障分析缺少三個非空欄位")
    return {field: analysis[field] for field in WRITE_FIELDS}


def write_ai_analysis(notice_number: str, values: dict[str, str]) -> None:
    client = MMISSession(MMISConfig.from_env())
    client.login()
    FaultNoticeAnalysisWriter(client).run(notice_number, values)


def mark_analysis_written(notice_number: str, database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _check_schema(connection)
        cursor = connection.execute(
            f'UPDATE {TABLE_NAME} SET "備註" = ? WHERE "通報號" = ? '
            'AND "Sufficient Data for Fault Analysis" = 1 '
            'AND "Fault Analysis Completed" = 0 AND "備註" IS NULL',
            ("填寫故障分析完成", notice_number),
        )
        if cursor.rowcount != 1:
            raise MMISClientError("故障分析已寫入 MMIS，但本機備註更新條件不符")


def move_to_waiting(
    notice_number: str,
    checks: tuple[int | None, ...],
    database_path: Path,
    waiting_database_path: Path,
    state: SyncState,
) -> None:
    connection = sqlite3.connect(database_path)
    transaction_started = False
    try:
        connection.execute("ATTACH DATABASE ? AS waiting", (str(waiting_database_path),))
        if any(
            connection.execute(f"PRAGMA {name}.journal_mode").fetchone()[0].lower() == "wal"
            for name in ("main", "waiting")
        ):
            raise MMISClientError("等候結案搬移需要兩個資料庫使用非 WAL journal mode")
        connection.execute("BEGIN IMMEDIATE")
        transaction_started = True
        state.waiting_transaction_started = True
        _check_schema(connection)
        _check_waiting_schema(connection, "waiting")
        stored = connection.execute(
            f'SELECT "事故等級", {DETAIL_CHECK_SELECT} '
            f'FROM {TABLE_NAME} WHERE "通報號" = ?',
            (notice_number,),
        ).fetchone()
        if stored != ("A", *checks) or not is_awaiting_closure("A", checks):
            raise MMISClientError("等候結案通報的主資料不符")
        added_at = current_added_at()
        connection.execute(
            f'INSERT INTO waiting.{WAITING_TABLE_NAME} ("通報號", "新增日期") '
            "VALUES (?, ?)",
            (notice_number, added_at),
        )
        deleted = connection.execute(
            f'DELETE FROM {TABLE_NAME} WHERE "通報號" = ?',
            (notice_number,),
        )
        waiting_row = connection.execute(
            f'SELECT "新增日期" FROM waiting.{WAITING_TABLE_NAME} '
            'WHERE "通報號" = ?',
            (notice_number,),
        ).fetchone()
        if deleted.rowcount != 1 or waiting_row != (added_at,):
            raise MMISClientError("等候結案通報搬移驗證失敗")
        connection.commit()
        state.waiting_added += 1
    except Exception:
        if transaction_started:
            try:
                connection.rollback()
                state.waiting_rolled_back = True
            except sqlite3.Error:
                pass
        raise
    finally:
        connection.close()


def execute(
    args: Sequence[str], *, database_path: Path | None = None,
    waiting_database_path: Path | None = None,
    state: SyncState | None = None,
) -> dict[str, Any]:
    if len(args) != len(set(args)) or set(args) - {
        "--check-analysis-readiness", "--export-xlsx"
    }:
        raise MMISClientError(f"用法: {USAGE}")
    check_analysis_readiness = "--check-analysis-readiness" in args
    export_requested = "--export-xlsx" in args
    state = state if state is not None else SyncState()
    state.export_requested = export_requested
    all_rows = prepare_rows(fetch_unclosed_fault_notices())
    state.records_fetched = len(all_rows)
    path = database_path or DATABASE_PATH
    waiting_path = waiting_database_path or path.with_name(WAITING_DATABASE_NAME)
    waiting_numbers = load_waiting_notice_numbers(waiting_path)
    recheck_all = waiting_recheck_pending(waiting_path)
    if recheck_all:
        waiting_numbers = set()
    number_index = BASIC_FIELDS.index("通報號")
    rows = [row for row in all_rows if row[number_index] not in waiting_numbers]
    state.records_skipped_waiting = len(all_rows) - len(rows)
    state.records_loaded = len(rows)
    saved = replace_rows(
        rows, path, state,
        waiting_database_path=waiting_path if recheck_all else None,
    )
    state.waiting_rechecked = recheck_all
    state.snapshot_saved = True
    for row in rows:
        notice_number = row[number_index]
        if check_analysis_readiness:
            state.readiness_queries += 1
        detail = fetch_fault_notice_detail(
            notice_number, check_analysis_readiness=check_analysis_readiness
        )
        checks = prepare_detail_checks(
            detail, notice_number, require_readiness=check_analysis_readiness
        )
        update_detail_checks(notice_number, checks, path, state)
        state.details_processed += 1
        if not check_analysis_readiness and checks[1] == 0:
            state.readiness_queries += 1
            try:
                readiness_detail = fetch_fault_notice_detail(
                    notice_number, check_analysis_readiness=True
                )
            except AnalysisEvidenceIncomplete as exc:
                state.readiness_unresolved.append({
                    "notice_number": notice_number, "reason": str(exc),
                })
                continue
            readiness_checks = prepare_detail_checks(
                readiness_detail, notice_number, require_readiness=True
            )
            update_analysis_readiness(
                notice_number, readiness_checks[0], path, state
            )
        elif check_analysis_readiness:
            state.readiness_saved += 1
        if is_awaiting_closure(row[BASIC_FIELDS.index("事故等級")], checks):
            move_to_waiting(notice_number, checks, path, waiting_path, state)
    result = {
        "success": not state.readiness_unresolved,
        "status": "partial_success" if state.readiness_unresolved else "success",
        "database": str(DATABASE_RELATIVE_PATH).replace("\\", "/"),
        "table": TABLE_NAME,
        "records_fetched": len(all_rows),
        "records_skipped_waiting": state.records_skipped_waiting,
        "waiting_rechecked": recheck_all,
        "records_loaded": saved,
        "records_saved": saved - state.waiting_added,
        "sync_mode": "full_replace",
        "detail_records_processed": state.details_processed,
        "detail_checks_saved": 5 * (state.details_processed - state.waiting_added)
        + state.readiness_saved - (state.waiting_added if check_analysis_readiness else 0),
        "analysis_readiness_queries": state.readiness_queries,
        "analysis_readiness_saved": state.readiness_saved,
        "analysis_readiness_unresolved": state.readiness_unresolved,
        "awaiting_closure_database": str(WAITING_DATABASE_RELATIVE_PATH).replace("\\", "/"),
        "awaiting_closure_added": state.waiting_added,
        "awaiting_closure_total": len(waiting_numbers) + state.waiting_added,
        "analysis_readiness": (
            "partial" if state.readiness_unresolved else
            "completed" if state.readiness_queries else "not_run"
        ),
    }
    if result["success"]:
        pending = pending_analysis_numbers(path)
        result["fault_analysis_candidates"] = len(pending)
        for notice_number in pending:
            state.analysis_target = notice_number
            values = fetch_ai_analysis(notice_number)
            write_ai_analysis(notice_number, values)
            mark_analysis_written(notice_number, path)
            state.analysis_written += 1
            state.analysis_target = None
    result["fault_analysis_written"] = state.analysis_written
    if export_requested:
        result["operation"] = "sync_and_export_xlsx"
        if not result["success"]:
            result["xlsx_export"] = {
                "status": "skipped", "reason": "SQLite 同步尚有未完成的資料充分性檢查",
            }
            return result
        state.sync_completed = True
        from . import export_unclosed_ab_fault_notices_from_db

        result["xlsx_export"] = export_unclosed_ab_fault_notices_from_db.execute(
            [], database_path=path, expected_records=result["records_saved"],
        )["xlsx_export"]
    return result


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
            "snapshot_saved": state.snapshot_saved,
            "detail_transaction_started": state.detail_transaction_started,
            "detail_rolled_back": state.detail_rolled_back,
            "detail_updated": state.detail_updated,
            "detail_records_processed": state.details_processed,
            "analysis_readiness_queries": state.readiness_queries,
            "analysis_readiness_saved": state.readiness_saved,
            "analysis_readiness_unresolved": state.readiness_unresolved,
            "waiting_transaction_started": state.waiting_transaction_started,
            "waiting_rolled_back": state.waiting_rolled_back,
            "awaiting_closure_added": state.waiting_added,
            "records_fetched": state.records_fetched,
            "records_skipped_waiting": state.records_skipped_waiting,
            "waiting_rechecked": state.waiting_rechecked,
            "records_loaded": state.records_loaded,
            "fault_analysis_current_notice": state.analysis_target,
            "fault_analysis_written": state.analysis_written,
        }
        if state.export_requested:
            result["operation"] = "sync_and_export_xlsx"
            result["sqlite_sync_success"] = state.sync_completed
            if state.sync_completed:
                result["database"] = str(DATABASE_RELATIVE_PATH).replace("\\", "/")
                result["table"] = TABLE_NAME
                result["records_saved"] = state.records_loaded - state.waiting_added
            result["xlsx_export"] = {
                "status": "failed" if state.sync_completed else "not_run",
                "reason": message if state.sync_completed else "SQLite 同步失敗",
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
