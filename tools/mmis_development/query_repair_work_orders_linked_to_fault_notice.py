from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.repair_work_orders import RepairWorkOrdersReader
from mmis_connector.fault_notices.reader import normalize_fault_notice

from ._support import run_json_tool


USAGE = (
    "python -m tools.mmis_development.query_repair_work_orders_linked_to_fault_notice "
    "<通報號>"
)


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    notice = normalize_fault_notice(args[0])
    client = MMISSession(MMISConfig.from_env())
    client.login()
    return RepairWorkOrdersReader(client).run(notice)


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
