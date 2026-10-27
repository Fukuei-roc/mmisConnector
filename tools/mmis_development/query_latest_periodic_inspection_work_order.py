from __future__ import annotations

from collections.abc import Sequence

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.periodic_inspection.query import LatestPeriodicInspectionWorkOrderQuery

from ._support import run_json_tool


USAGE = (
    "python -m tools.mmis_development.query_latest_periodic_inspection_work_order "
    "<車組/車號>"
)


def execute(args: Sequence[str]) -> dict[str, str]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    return LatestPeriodicInspectionWorkOrderQuery(
        MMISSession(MMISConfig.from_env())
    ).run(args[0])


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
