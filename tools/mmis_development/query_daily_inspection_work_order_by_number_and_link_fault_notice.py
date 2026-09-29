from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.linker import (
    DailyInspectionWorkOrderFaultNoticeLinker,
)

from ._support import run_json_tool


USAGE = (
    "python -m "
    "tools.mmis_development."
    "query_daily_inspection_work_order_by_number_and_link_fault_notice "
    "<工作單號> <故障通報號>"
)


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 2:
        raise MMISClientError(f"用法: {USAGE}")
    client = MMISSession(MMISConfig.from_env())
    return DailyInspectionWorkOrderFaultNoticeLinker(client).run(
        args[0], args[1]
    )


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
