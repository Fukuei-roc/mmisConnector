from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.periodic_inspection.query import LatestPeriodicInspectionWorkOrderQuery
from mmis_connector.periodic_inspection.workbook import (
    DEFAULT_WORKBOOK,
    fill_latest_periodic_inspection_work_orders,
    load_validated_workbook,
)


USAGE = (
    "python -m tools.mmis_development.fill_latest_periodic_inspection_work_orders "
    "[--workbook <Excel 路徑>]"
)


def execute(args: Sequence[str]) -> dict[str, object]:
    if not args:
        path = DEFAULT_WORKBOOK
    elif len(args) == 2 and args[0] == "--workbook":
        path = Path(args[1])
    else:
        raise MMISClientError(f"用法: {USAGE}")
    workbook = load_validated_workbook(path)
    try:
        config = MMISConfig.from_env()
        return fill_latest_periodic_inspection_work_orders(
            workbook,
            path,
            lambda: LatestPeriodicInspectionWorkOrderQuery(MMISSession(config)),
        ).as_dict()
    finally:
        workbook.close()


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        result = execute(list(sys.argv[1:] if argv is None else argv))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1
    except KeyboardInterrupt:
        print(json.dumps({"success": False, "message": "使用者中止；已儲存先前成功的列"}, ensure_ascii=False))
        return 130
    except Exception as exc:
        message = (
            str(exc)
            if isinstance(exc, MMISClientError)
            else "發生未預期錯誤；已隱藏詳細內容以避免洩漏敏感資料"
        )
        print(json.dumps({"success": False, "error": type(exc).__name__, "message": message}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
