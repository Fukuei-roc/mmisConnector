from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4


DEFAULT_DATABASE_PATH = Path("data/auto_link_unprocessed_fault_notices.sqlite3")

SOURCE_FIELDS = (
    ("車次", "train_no"),
    ("車組/車號", "vehicle"),
    ("發生日期", "occurrence_date"),
    ("發生時間", "occurrence_time"),
    ("事故等級", "incident_level"),
    ("故障地點", "fault_location"),
    ("ATP故障", "atp_fault"),
    ("故障現象", "fault_symptom"),
    ("立案人員", "case_creator"),
    ("通報人員", "reporter"),
    ("通報單位", "reporting_unit"),
    ("通報股室", "reporting_section"),
    ("狀態", "source_status"),
    ("通報號", "fault_notice_no"),
    ("配屬段別", "assigned_depot_code"),
    ("配屬段別名稱", "assigned_depot_name"),
    ("顏色查詢", "color_query"),
)

PROCESSING_STATUSES = frozenset(
    {
        "pending",
        "query_failed",
        "invalid_source_data",
        "no_matching_work_order",
        "ambiguous_work_order",
        "work_order_selected",
        "linking",
        "linked",
        "link_error",
    }
)
RETRYABLE_STATUSES = ("pending", "query_failed", "work_order_selected")
UNSETTLED_STATUSES = (*RETRYABLE_STATUSES, "linking", "link_error")
LINK_INTERRUPTED_MESSAGE = "前次勾稽結果不明，需人工確認；程式未自動重送"


@dataclass(frozen=True)
class RunPreparation:
    run_id: str
    resumed: bool
    source_loaded: bool


class AutoLinkStore:
    """Persist one recoverable auto-link batch in SQLite."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> AutoLinkStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def execution_lock(self):
        """Prevent two processes from running the same batch concurrently."""
        lock_path = self.path.with_name(f"{self.path.name}.lock.sqlite3")
        lock_connection = sqlite3.connect(lock_path, timeout=0)
        try:
            lock_connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_lock (id INTEGER PRIMARY KEY)"
            )
            lock_connection.commit()
            try:
                lock_connection.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                raise RuntimeError("已有另一個自動勾稽程序正在執行") from exc
            yield
        finally:
            lock_connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _initialize_schema(self) -> None:
        source_columns = ",\n".join(
            f"{column} TEXT" for _, column in SOURCE_FIELDS
        )
        self.connection.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK (status IN ('running', 'completed')),
                source_loaded INTEGER NOT NULL DEFAULT 0
                    CHECK (source_loaded IN (0, 1)),
                source_query_name TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS fault_notices (
                id INTEGER PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                source_index INTEGER NOT NULL,
                {source_columns},
                source_record_json TEXT NOT NULL,
                daily_inspection_work_order_no TEXT,
                processing_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (processing_status IN (
                        'pending',
                        'query_failed',
                        'invalid_source_data',
                        'no_matching_work_order',
                        'ambiguous_work_order',
                        'work_order_selected',
                        'linking',
                        'linked',
                        'link_error'
                    )),
                result_message TEXT,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (run_id, source_index),
                UNIQUE (run_id, fault_notice_no)
            );

            CREATE INDEX IF NOT EXISTS idx_fault_notices_run_status
            ON fault_notices(run_id, processing_status, source_index);
            """
        )
        self.connection.commit()

    def prepare_run(self) -> RunPreparation:
        now = self._now()
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            active = self.connection.execute(
                """
                SELECT run_id, source_loaded
                FROM runs
                WHERE status = 'running'
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
            if active is not None:
                run_id = str(active["run_id"])
                self.connection.execute(
                    """
                    UPDATE fault_notices
                    SET processing_status = 'link_error',
                        result_message = ?,
                        updated_at = ?
                    WHERE run_id = ? AND processing_status = 'linking'
                    """,
                    (LINK_INTERRUPTED_MESSAGE, now, run_id),
                )
                return RunPreparation(
                    run_id=run_id,
                    resumed=True,
                    source_loaded=bool(active["source_loaded"]),
                )

            self.connection.execute("DELETE FROM fault_notices")
            self.connection.execute("DELETE FROM runs")
            run_id = uuid4().hex
            self.connection.execute(
                """
                INSERT INTO runs(run_id, status, source_loaded, started_at)
                VALUES (?, 'running', 0, ?)
                """,
                (run_id, now),
            )
            return RunPreparation(run_id, resumed=False, source_loaded=False)

    @staticmethod
    def _source_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def import_source_records(
        self,
        run_id: str,
        query_name: str,
        records: Iterable[Mapping[str, Any]],
    ) -> None:
        now = self._now()
        columns = [column for _, column in SOURCE_FIELDS]
        placeholders = ", ".join("?" for _ in range(len(columns) + 6))
        sql = f"""
            INSERT INTO fault_notices(
                run_id, source_index, {', '.join(columns)},
                source_record_json, processing_status, created_at, updated_at
            ) VALUES ({placeholders})
        """
        with self.connection:
            run = self.connection.execute(
                "SELECT source_loaded FROM runs WHERE run_id = ? AND status = 'running'",
                (run_id,),
            ).fetchone()
            if run is None:
                raise ValueError("找不到可匯入來源資料的執行批次")
            if bool(run["source_loaded"]):
                raise ValueError("此執行批次已匯入來源資料")

            for source_index, record in enumerate(records, start=1):
                values = [
                    self._source_value(record.get(header))
                    for header, _ in SOURCE_FIELDS
                ]
                fault_notice_index = columns.index("fault_notice_no")
                if not values[fault_notice_index].strip():
                    values[fault_notice_index] = None
                source_json = json.dumps(
                    dict(record), ensure_ascii=False, sort_keys=True, default=str
                )
                self.connection.execute(
                    sql,
                    (
                        run_id,
                        source_index,
                        *values,
                        source_json,
                        "pending",
                        now,
                        now,
                    ),
                )

            self.connection.execute(
                """
                UPDATE runs
                SET source_loaded = 1, source_query_name = ?
                WHERE run_id = ?
                """,
                (query_name, run_id),
            )

    def list_processable(self, run_id: str) -> list[dict[str, Any]]:
        placeholders = ", ".join("?" for _ in RETRYABLE_STATUSES)
        rows = self.connection.execute(
            f"""
            SELECT * FROM fault_notices
            WHERE run_id = ? AND processing_status IN ({placeholders})
            ORDER BY source_index
            """,
            (run_id, *RETRYABLE_STATUSES),
        ).fetchall()
        return [dict(row) for row in rows]

    def begin_attempt(self, run_id: str, row_id: int) -> None:
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE fault_notices
                SET attempt_count = attempt_count + 1, updated_at = ?
                WHERE run_id = ? AND id = ?
                """,
                (self._now(), run_id, row_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("找不到要處理的故障通報資料")

    def set_status(
        self,
        run_id: str,
        row_id: int,
        status: str,
        *,
        work_order_no: str | None = None,
        message: str | None = None,
    ) -> None:
        if status not in PROCESSING_STATUSES:
            raise ValueError(f"不支援的處理狀態：{status}")
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE fault_notices
                SET processing_status = ?,
                    daily_inspection_work_order_no = COALESCE(
                        ?, daily_inspection_work_order_no
                    ),
                    result_message = ?,
                    updated_at = ?
                WHERE run_id = ? AND id = ?
                """,
                (status, work_order_no, message, self._now(), run_id, row_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("找不到要更新的故障通報資料")

    def get_row(self, run_id: str, row_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM fault_notices WHERE run_id = ? AND id = ?",
            (run_id, row_id),
        ).fetchone()
        if row is None:
            raise ValueError("找不到故障通報資料")
        return dict(row)

    def complete_if_settled(self, run_id: str) -> bool:
        placeholders = ", ".join("?" for _ in UNSETTLED_STATUSES)
        with self.connection:
            unsettled = self.connection.execute(
                f"""
                SELECT COUNT(*)
                FROM fault_notices
                WHERE run_id = ? AND processing_status IN ({placeholders})
                """,
                (run_id, *UNSETTLED_STATUSES),
            ).fetchone()[0]
            if unsettled:
                return False
            self.connection.execute(
                """
                UPDATE runs
                SET status = 'completed', completed_at = ?
                WHERE run_id = ? AND status = 'running'
                """,
                (self._now(), run_id),
            )
            return True

    def summary(self, run_id: str) -> dict[str, int]:
        rows = self.connection.execute(
            """
            SELECT processing_status, COUNT(*) AS count
            FROM fault_notices
            WHERE run_id = ?
            GROUP BY processing_status
            """,
            (run_id,),
        ).fetchall()
        counts = {status: 0 for status in PROCESSING_STATUSES}
        counts.update({str(row["processing_status"]): int(row["count"]) for row in rows})
        counts["total"] = sum(int(row["count"]) for row in rows)
        return counts
