from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.reader import (
    DailyInspectionWorkOrderDetailReader,
)

from ._support import run_json_tool


USAGE = (
    "python -m "
    "tools.mmis_development.query_daily_inspection_work_order_by_number "
    "<工作單號>"
)


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    client = MMISSession(MMISConfig.from_env())
    return DailyInspectionWorkOrderDetailReader(client).run(args[0])


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
