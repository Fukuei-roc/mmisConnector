from __future__ import annotations

import json
import sys
from collections.abc import Sequence

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.periodic_inspection.air_hose_workbook import (
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE,
    query_air_hose_dates_to_workbook,
)
from mmis_connector.periodic_inspection.reader import (
    PeriodicInspectionWorkOrderDetailReader,
)


USAGE = "python -m tools.mmis_development.auto_query_air_hose_dates"


def execute(args: Sequence[str]) -> dict[str, object]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    config = MMISConfig.from_env()
    result = query_air_hose_dates_to_workbook(
        DEFAULT_SOURCE,
        DEFAULT_OUTPUT,
        lambda: PeriodicInspectionWorkOrderDetailReader(
            MMISSession(config)
        ),
    )
    return {**result.as_dict(), "output_file": str(DEFAULT_OUTPUT)}


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        result = execute(list(sys.argv[1:] if argv is None else argv))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1
    except KeyboardInterrupt:
        print(json.dumps(
            {"success": False, "message": "使用者中止；已保留先前成功的工作單"},
            ensure_ascii=False,
        ))
        return 130
    except Exception as exc:
        message = (
            str(exc) if isinstance(exc, MMISClientError)
            else "發生未預期錯誤；已隱藏詳細內容以避免洩漏敏感資料"
        )
        print(json.dumps(
            {"success": False, "error": type(exc).__name__, "message": message},
            ensure_ascii=False, indent=2,
        ))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
