from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from typing import Any

from .auth import MMISClientError, MMISConfig, MMISSession
from .query_daily_inspection_work_orders_by_vehicle_and_date import (
    DailyInspectionWorkOrderQuery,
)
from .query_unprocessed_fault_notices import UnprocessedFaultNoticeQuery
from .query_fault_notices_linked_to_daily_inspection_work_order_by_number import (
    DailyInspectionWorkOrderDetailReader,
)


QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND = "query-unprocessed-fault-notices"
QUERY_DAILY_INSPECTION_WORK_ORDERS_BY_VEHICLE_AND_DATE_COMMAND = (
    "query-daily-inspection-work-orders-by-vehicle-and-date"
)
QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_COMMAND = (
    "query-daily-inspection-work-order-by-number"
)
CommandHandler = Callable[[Sequence[str]], dict[str, Any]]


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _query_unprocessed_fault_notices(args: Sequence[str]) -> dict[str, Any]:
    if args:
        raise MMISClientError(
            f"用法: {QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND}"
        )
    config = MMISConfig.from_env()
    client = MMISSession(config)
    client.login()
    return UnprocessedFaultNoticeQuery(client).run()


def _query_daily_inspection_work_orders_by_vehicle_and_date(
    args: Sequence[str],
) -> dict[str, Any]:
    if len(args) != 2:
        raise MMISClientError(
            "用法: "
            f"{QUERY_DAILY_INSPECTION_WORK_ORDERS_BY_VEHICLE_AND_DATE_COMMAND} "
            "<車組/車號> <檢修日期條件 [=|>|<|>=|<=]YYYY/MM/DD>"
        )
    config = MMISConfig.from_env()
    client = MMISSession(config)
    return DailyInspectionWorkOrderQuery(client).run(args[0], args[1])


def _query_daily_inspection_work_order_by_number(
    args: Sequence[str],
) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(
            f"用法: {QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_COMMAND} "
            "<工作單號>"
        )
    config = MMISConfig.from_env()
    client = MMISSession(config)
    return DailyInspectionWorkOrderDetailReader(client).run(args[0])


def _commands() -> dict[str, CommandHandler]:
    return {
        QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND: _query_unprocessed_fault_notices,
        QUERY_DAILY_INSPECTION_WORK_ORDERS_BY_VEHICLE_AND_DATE_COMMAND: (
            _query_daily_inspection_work_orders_by_vehicle_and_date
        ),
        QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_COMMAND: (
            _query_daily_inspection_work_order_by_number
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    args = list(sys.argv[1:] if argv is None else argv)
    commands = _commands()
    try:
        if not args or args[0] not in commands:
            available = ", ".join(sorted(commands))
            raise MMISClientError(
                "請指定一個有效功能子命令。可用命令: " + available
            )
        result = commands[args[0]](args[1:])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        message = (
            str(exc)
            if isinstance(exc, MMISClientError)
            else "發生未預期錯誤；已隱藏詳細內容以避免洩漏敏感資料"
        )
        error = {
            "success": False,
            "error": type(exc).__name__,
            "message": message,
        }
        print(json.dumps(error, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
