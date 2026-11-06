from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import logging
import re
from typing import Any, Protocol

from ..auth import MMISClientError, MMISSession
from ..daily_inspection.linker import (
    DailyInspectionWorkOrderFaultNoticeLinker,
    normalize_fault_notice,
)
from ..daily_inspection.query import (
    DEPOT,
    WORK_ORDER_STATUS,
    DailyInspectionWorkOrderQuery,
    normalize_inspection_date,
    normalize_vehicle,
)
from ..daily_inspection.reader import DailyInspectionWorkOrderDetailReader
from ..fault_notices.query import UnprocessedFaultNoticeQuery
from ..run_logging import log_event
from .store import AutoLinkStore


OPERATION_NAME = "自動勾稽日檢未處理通報"
GENERIC_QUERY_ERROR = "查詢發生未預期錯誤；詳細內容未儲存以避免洩漏敏感資料"
GENERIC_LINK_ERROR = "勾稽發生未預期錯誤；需人工確認且程式不會自動重送"
LOGGER = logging.getLogger("mmis_connector.auto_link")


class _Runner(Protocol):
    def run(self, *args: str) -> dict[str, Any]: ...


RunnerFactory = Callable[[MMISSession], _Runner]
NON_DIGIT_RE = re.compile(r"[^0-9]")


@dataclass(frozen=True)
class WorkOrderSelection:
    status: str
    work_order_no: str | None
    message: str


def normalize_auto_link_vehicle(value: str) -> str:
    """Convert a source car identifier to the 1A work-order query value."""
    source_vehicle = normalize_vehicle(value)
    digits = NON_DIGIT_RE.sub("", source_vehicle)
    if not digits:
        raise MMISClientError("車組/車號必須包含數字")
    if len(digits) == 4 and digits.startswith("9"):
        return digits[:-1]
    return digits


def _parse_date(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise MMISClientError(f"{field_name}不是有效字串")
    normalized = normalize_inspection_date(value)
    return datetime.strptime(normalized, "%Y/%m/%d")


def select_earliest_work_order(
    records: Sequence[Mapping[str, Any]], occurrence_date: str
) -> WorkOrderSelection:
    occurred_at = _parse_date(occurrence_date, field_name="發生日期")
    candidates: list[tuple[datetime, str]] = []
    for record in records:
        raw_work_order = record.get("工作單")
        if not isinstance(raw_work_order, str) or not raw_work_order.strip():
            raise MMISClientError("日檢工單查詢結果缺少工作單號")
        inspected_at = _parse_date(record.get("檢修日期"), field_name="檢修日期")
        if inspected_at > occurred_at:
            candidates.append((inspected_at, raw_work_order.strip()))

    if not candidates:
        return WorkOrderSelection(
            "no_matching_work_order", None, "查詢不到對應工單"
        )

    earliest_date = min(date for date, _ in candidates)
    earliest_orders = sorted(
        {work_order for date, work_order in candidates if date == earliest_date}
    )
    if len(earliest_orders) != 1:
        return WorkOrderSelection(
            "ambiguous_work_order",
            None,
            "最早檢修日期有多筆不同工作單，未執行勾稽",
        )
    return WorkOrderSelection(
        "work_order_selected", earliest_orders[0], "已選擇最早檢修日期的工作單"
    )


def _safe_error_message(exc: Exception, *, link: bool) -> str:
    if isinstance(exc, MMISClientError):
        return str(exc)[:500]
    return GENERIC_LINK_ERROR if link else GENERIC_QUERY_ERROR


class AutoLinkUnprocessedFaultNotices:
    """Orchestrate the recoverable unprocessed-fault auto-link workflow."""

    def __init__(
        self,
        client: MMISSession,
        store: AutoLinkStore,
        *,
        source_query_factory: RunnerFactory = UnprocessedFaultNoticeQuery,
        work_order_query_factory: RunnerFactory = DailyInspectionWorkOrderQuery,
        linker_factory: RunnerFactory = DailyInspectionWorkOrderFaultNoticeLinker,
        detail_reader_factory: RunnerFactory = DailyInspectionWorkOrderDetailReader,
    ) -> None:
        self.client = client
        self.store = store
        self.source_query = source_query_factory(client)
        self.work_order_query = work_order_query_factory(client)
        self.linker = linker_factory(client)
        self.detail_reader = detail_reader_factory(client)

    def _reconcile_link_errors(self, run_id: str) -> None:
        for row in self.store.list_link_errors(run_id):
            work_order = row["daily_inspection_work_order_no"]
            fault_notice = row["fault_notice_no"]
            if not isinstance(work_order, str) or not isinstance(fault_notice, str):
                continue
            log_event(
                LOGGER, "link_reconciliation_started",
                run_id=run_id, fault_notice_no=fault_notice, work_order_no=work_order,
            )
            try:
                result = self.detail_reader.run(work_order)
            except Exception as exc:
                log_event(
                    LOGGER, "link_reconciliation_failed",
                    run_id=run_id, fault_notice_no=fault_notice,
                    work_order_no=work_order, error_type=type(exc).__name__,
                    message=_safe_error_message(exc, link=True),
                )
                continue
            confirmed = (
                result.get("success") is True
                and result.get("work_order") == work_order
                and isinstance(result.get("records"), list)
                and result.get("count") == len(result["records"])
                and any(
                    isinstance(record, dict)
                    and record.get("故障通報號") == fault_notice
                    for record in result["records"]
                )
            )
            if confirmed:
                self.store.set_status(
                    run_id, int(row["id"]), "linked", message="唯讀核對確認勾稽成功"
                )
            log_event(
                LOGGER, "link_reconciliation_result",
                run_id=run_id, fault_notice_no=fault_notice,
                work_order_no=work_order, confirmed=confirmed,
            )

    def _load_source_if_needed(
        self, run_id: str, *, source_loaded: bool
    ) -> None:
        if source_loaded:
            log_event(LOGGER, "source_reused", run_id=run_id)
            return
        log_event(LOGGER, "source_query_started", run_id=run_id)
        result = self.source_query.run()
        records = result.get("records")
        count = result.get("count")
        query_name = result.get("query_name")
        if (
            result.get("success") is not True
            or not isinstance(records, list)
            or not isinstance(count, int)
            or count != len(records)
            or not isinstance(query_name, str)
        ):
            raise MMISClientError("本段未處理通報查詢結果格式不正確")
        self.store.import_source_records(run_id, query_name, records)
        log_event(LOGGER, "source_query_completed", run_id=run_id, count=count)

    @staticmethod
    def _validated_source(row: Mapping[str, Any]) -> tuple[str, str, str]:
        vehicle = normalize_auto_link_vehicle(str(row.get("vehicle") or ""))
        occurrence_date = normalize_inspection_date(
            str(row.get("occurrence_date") or "")
        )
        fault_notice = normalize_fault_notice(
            str(row.get("fault_notice_no") or "")
        )
        return vehicle, occurrence_date, fault_notice

    def _query_work_order(
        self, vehicle: str, occurrence_date: str, *,
        run_id: str, fault_notice: str, source_index: int,
    ) -> WorkOrderSelection:
        log_event(
            LOGGER, "work_order_query_started",
            run_id=run_id, fault_notice_no=fault_notice,
            source_index=source_index, vehicle=vehicle,
            date_condition=f">{occurrence_date}", depot=DEPOT,
            work_order_status_filter=WORK_ORDER_STATUS,
        )
        result = self.work_order_query.run(vehicle, f">{occurrence_date}")
        records = result.get("records")
        count = result.get("count")
        if (
            result.get("success") is not True
            or not isinstance(records, list)
            or not isinstance(count, int)
            or count != len(records)
        ):
            raise MMISClientError("日檢工單查詢結果格式不正確")
        log_event(
            LOGGER, "work_order_query_completed",
            run_id=run_id, fault_notice_no=fault_notice,
            source_index=source_index, count=count,
            candidates=[
                {
                    "work_order_no": record.get("工作單"),
                    "inspection_date": record.get("檢修日期"),
                    "vehicle": record.get("車組/車號"),
                    "status": record.get("工作單狀態"),
                }
                for record in records
            ],
        )
        return select_earliest_work_order(records, occurrence_date)

    def _process_row(self, run_id: str, row: Mapping[str, Any]) -> None:
        row_id = int(row["id"])
        source_index = int(row["source_index"])
        self.store.begin_attempt(run_id, row_id)
        try:
            vehicle, occurrence_date, fault_notice = self._validated_source(row)
        except Exception as exc:  # validation boundary for one source row
            self.store.set_status(
                run_id,
                row_id,
                "invalid_source_data",
                message=_safe_error_message(exc, link=False),
            )
            log_event(
                LOGGER, "source_invalid", run_id=run_id,
                source_index=source_index,
                fault_notice_no=row.get("fault_notice_no"),
                error_type=type(exc).__name__,
                message=_safe_error_message(exc, link=False),
            )
            return

        log_event(
            LOGGER, "source_validated", run_id=run_id,
            source_index=source_index, fault_notice_no=fault_notice,
            source_vehicle=row.get("vehicle"), query_vehicle=vehicle,
            occurrence_date=occurrence_date,
        )

        work_order_no = row.get("daily_inspection_work_order_no")
        if row.get("processing_status") != "work_order_selected":
            try:
                selection = self._query_work_order(
                    vehicle, occurrence_date, run_id=run_id,
                    fault_notice=fault_notice, source_index=source_index,
                )
            except Exception as exc:  # one query failure must not stop the batch
                self.store.set_status(
                    run_id,
                    row_id,
                    "query_failed",
                    message=_safe_error_message(exc, link=False),
                )
                log_event(
                    LOGGER, "work_order_query_failed",
                    run_id=run_id, source_index=source_index,
                    fault_notice_no=fault_notice, error_type=type(exc).__name__,
                    message=_safe_error_message(exc, link=False),
                )
                return
            log_event(
                LOGGER, "work_order_selection",
                run_id=run_id, source_index=source_index,
                fault_notice_no=fault_notice, status=selection.status,
                work_order_no=selection.work_order_no,
            )
            if selection.work_order_no is None:
                self.store.set_status(
                    run_id,
                    row_id,
                    selection.status,
                    message=selection.message,
                )
                return
            work_order_no = selection.work_order_no
            self.store.set_status(
                run_id,
                row_id,
                "work_order_selected",
                work_order_no=work_order_no,
                message=selection.message,
            )

        if not isinstance(work_order_no, str) or not work_order_no.strip():
            self.store.set_status(
                run_id,
                row_id,
                "link_error",
                message="已選擇工單的狀態缺少工作單號，未執行勾稽",
            )
            log_event(
                LOGGER, "link_failed", run_id=run_id,
                source_index=source_index, fault_notice_no=fault_notice,
                status="link_error", message="已選擇工單的狀態缺少工作單號，未執行勾稽",
            )
            return

        self.store.set_status(
            run_id,
            row_id,
            "linking",
            work_order_no=work_order_no,
            message="勾稽處理中",
        )
        log_event(
            LOGGER, "link_started", run_id=run_id,
            source_index=source_index, fault_notice_no=fault_notice,
            work_order_no=work_order_no,
        )
        try:
            link_result = self.linker.run(work_order_no, fault_notice)
            if (
                link_result.get("success") is not True
                or link_result.get("linked") is not True
            ):
                raise MMISClientError("勾稽回傳結果格式不正確，需人工確認")
        except Exception as exc:  # no link failure may be retried automatically
            self.store.set_status(
                run_id,
                row_id,
                "link_error",
                work_order_no=work_order_no,
                message=_safe_error_message(exc, link=True),
            )
            log_event(
                LOGGER, "link_failed", run_id=run_id,
                source_index=source_index, fault_notice_no=fault_notice,
                work_order_no=work_order_no, error_type=type(exc).__name__,
                message=_safe_error_message(exc, link=True),
            )
            return
        self.store.set_status(
            run_id,
            row_id,
            "linked",
            work_order_no=work_order_no,
            message="勾稽成功",
        )
        log_event(
            LOGGER, "link_succeeded", run_id=run_id,
            source_index=source_index, fault_notice_no=fault_notice,
            work_order_no=work_order_no,
        )

    def _run_locked(self) -> dict[str, Any]:
        prepared = self.store.prepare_run()
        log_event(
            LOGGER, "run_prepared", run_id=prepared.run_id,
            resumed=prepared.resumed, source_loaded=prepared.source_loaded,
        )
        self._load_source_if_needed(
            prepared.run_id, source_loaded=prepared.source_loaded
        )
        if prepared.resumed:
            self._reconcile_link_errors(prepared.run_id)
        for row in self.store.list_processable(prepared.run_id):
            self._process_row(prepared.run_id, row)

        completed = self.store.complete_if_settled(prepared.run_id)
        counts = self.store.summary(prepared.run_id)
        log_event(
            LOGGER, "run_completed", run_id=prepared.run_id,
            completed=completed, counts=counts,
        )
        failed = sum(
            counts[status]
            for status in (
                "invalid_source_data",
                "ambiguous_work_order",
                "query_failed",
                "link_error",
            )
        )
        return {
            "success": True,
            "operation_name": OPERATION_NAME,
            "run_id": prepared.run_id,
            "resumed": prepared.resumed,
            "completed": completed,
            "total": counts["total"],
            "linked": counts["linked"],
            "no_matching_work_order": counts["no_matching_work_order"],
            "ambiguous_work_order": counts["ambiguous_work_order"],
            "invalid_source_data": counts["invalid_source_data"],
            "query_failed": counts["query_failed"],
            "link_error": counts["link_error"],
            "failed": failed,
            "manual_review_required": counts["link_error"],
            "database_path": str(self.store.path),
        }

    def run(self) -> dict[str, Any]:
        with self.store.execution_lock():
            return self._run_locked()
