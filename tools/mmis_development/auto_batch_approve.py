from __future__ import annotations

from collections.abc import Sequence

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.batch_approval import approve_all_pending

from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.auto_batch_approve"


def execute(args: Sequence[str]) -> dict[str, int]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    config = MMISConfig.from_env(credential_prefix="MMIS_DEPUTY")
    if config.username != "0776044":
        raise MMISClientError("MMIS_DEPUTY_USERNAME 必須是指定的副段長帳號")
    client = MMISSession(config)
    client.login()
    return approve_all_pending(client)


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
