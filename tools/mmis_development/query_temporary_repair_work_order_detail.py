from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.temporary_repair.reader import TemporaryRepairProcedureReader

from ._support import run_json_tool


USAGE = (
    "python -m tools.mmis_development."
    "query_temporary_repair_work_order_detail <工作單號>"
)


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    return TemporaryRepairProcedureReader(MMISSession(MMISConfig.from_env())).run(args[0])


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
