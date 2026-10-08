from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.reader import DailyInspectionInspectionRecordReader

from ._support import run_json_tool


USAGE = (
    "python -m "
    "tools.mmis_development.query_daily_inspection_work_order_inspection_records "
    "<工作單號>"
)


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    client = MMISSession(MMISConfig.from_env())
    result = DailyInspectionInspectionRecordReader(client).run(args[0])
    return {
        "success": result["success"],
        "query_name": result["query_name"],
        "work_order": result["work_order"],
        "檢修記錄": {"count": result["count"], "records": result["records"]},
        "重要事項紀錄": result["important_notes"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
