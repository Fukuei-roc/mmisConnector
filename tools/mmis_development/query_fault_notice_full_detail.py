from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.analysis_materials import collect_analysis_materials
from mmis_connector.fault_notices.full_detail import FaultNoticeFullDetailReader
from mmis_connector.fault_notices.reader import normalize_fault_notice
from mmis_connector.fault_notices.ai_analysis import analyze_fault_notice, merge_fault_analysis

from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.query_fault_notice_full_detail <通報號> [--ai-analysis]"
COMPLETION_FIELDS = ("故障原因", "處理情形", "改善對策")


def _fault_analysis_completed(analysis: dict[str, str]) -> bool:
    return all(bool(analysis[field].strip()) for field in COMPLETION_FIELDS)


def evaluate_depot_work_order_status(work_orders: Sequence[dict[str, Any]]) -> dict[str, bool]:
    statuses = [work_order.get("工作單狀態") for work_order in work_orders]
    return {
        "All Depot Maintenance Work Orders Closed": bool(statuses) and all(
            status == "工單結案" for status in statuses
        ),
        "Depot Maintenance Work Orders Pending Approval": any(
            status == "簽核中" for status in statuses
        ),
    }


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) not in (1, 2) or (len(args) == 2 and args[1] != "--ai-analysis"):
        raise MMISClientError(f"用法: {USAGE}")
    notice = normalize_fault_notice(args[0])
    client = MMISSession(MMISConfig.from_env())
    client.login()
    result = FaultNoticeFullDetailReader(client).run(notice)
    result["Fault Analysis Completed"] = _fault_analysis_completed(result["故障分析"])
    result.update(evaluate_depot_work_order_status(result["段修工單"]))
    result["故障分析素材"] = collect_analysis_materials(client, result["段修工單"])
    if len(args) == 2:
        result = merge_fault_analysis(result, analyze_fault_notice(result))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
