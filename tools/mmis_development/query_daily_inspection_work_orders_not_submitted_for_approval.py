from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.not_submitted import DailyInspectionNotSubmittedQuery

from ._support import run_json_tool


def execute(args: Sequence[str]) -> dict[str, Any]:
    if args:
        raise MMISClientError("此查詢不接受參數")
    return DailyInspectionNotSubmittedQuery(MMISSession(MMISConfig.from_env())).run()


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
