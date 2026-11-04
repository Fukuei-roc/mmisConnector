from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.cancel import DailyInspectionWorkOrderCanceller

from ._support import run_json_tool


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError("用法: python -m tools.mmis_development.delete_unassigned_daily_inspection_work_order <工作單>")
    return DailyInspectionWorkOrderCanceller(MMISSession(MMISConfig.from_env())).run(args[0])


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
