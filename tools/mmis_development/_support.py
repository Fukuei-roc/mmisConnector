from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from typing import Any

from mmis_connector.auth import MMISClientError


ToolHandler = Callable[[Sequence[str]], dict[str, Any]]


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def run_json_tool(
    handler: ToolHandler,
    argv: Sequence[str] | None = None,
) -> int:
    """Run one thin development tool with the shared safe JSON contract."""
    _configure_stdio()
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        result = handler(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        message = (
            str(exc)
            if isinstance(exc, MMISClientError)
            else "發生未預期錯誤；已隱藏詳細內容以避免洩漏敏感資料"
        )
        print(
            json.dumps(
                {
                    "success": False,
                    "error": type(exc).__name__,
                    "message": message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
