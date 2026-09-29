from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.query import (
    UnprocessedFaultNoticeQuery,
)

from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.query_unprocessed_fault_notices"


def execute(args: Sequence[str]) -> dict[str, Any]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    client = MMISSession(MMISConfig.from_env())
    client.login()
    return UnprocessedFaultNoticeQuery(client).run()


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
