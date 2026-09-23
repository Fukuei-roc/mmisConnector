from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from typing import Any

from .auth import MMISClientError, MMISConfig, MMISSession
from .query_unprocessed_fault_notices import UnprocessedFaultNoticeQuery


QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND = "query-unprocessed-fault-notices"
CommandHandler = Callable[[], dict[str, Any]]


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _query_unprocessed_fault_notices() -> dict[str, Any]:
    config = MMISConfig.from_env()
    client = MMISSession(config)
    client.login()
    return UnprocessedFaultNoticeQuery(client).run()


def _commands() -> dict[str, CommandHandler]:
    return {
        QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND: _query_unprocessed_fault_notices,
    }


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    args = list(sys.argv[1:] if argv is None else argv)
    commands = _commands()
    try:
        if len(args) != 1 or args[0] not in commands:
            available = ", ".join(sorted(commands))
            raise MMISClientError(
                "請指定一個有效功能子命令。可用命令: " + available
            )
        result = commands[args[0]]()
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
