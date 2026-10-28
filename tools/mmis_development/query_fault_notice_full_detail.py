from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.analysis_materials import collect_analysis_materials
from mmis_connector.fault_notices.atp_reader import ATP_ANALYSIS_FIELDS
from mmis_connector.fault_notices.full_detail import FaultNoticeFullDetailReader
from mmis_connector.fault_notices.reader import normalize_fault_notice
from mmis_connector.fault_notices.ai_analysis import analyze_fault_notice, merge_fault_analysis
from mmis_connector.fault_notices.atp_ai_analysis import analyze_atp_fault
from mmis_connector.fault_notices.analysis_readiness import check_analysis_readiness

from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.query_fault_notice_full_detail <通報號> [--ai-analysis | --check-analysis-readiness]"
COMPLETION_FIELDS = ("故障原因", "處理情形", "改善對策")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise MMISClientError(f"用法: {USAGE}；{message}")


def _parse_args(args: Sequence[str]) -> argparse.Namespace:
    parser = _Parser(add_help=False)
    parser.add_argument("通報號")
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--ai-analysis", action="store_true")
    options.add_argument("--check-analysis-readiness", action="store_true")
    return parser.parse_args(args)


def _fault_analysis_completed(analysis: dict[str, str]) -> bool:
    return all(bool(analysis[field].strip()) for field in COMPLETION_FIELDS)


def _atp_fault_analysis_incomplete(atp_fault: bool, analysis: dict[str, str] | None) -> bool:
    return atp_fault and any(
        not str((analysis or {}).get(field) or "").strip()
        for field in ATP_ANALYSIS_FIELDS
    )


def evaluate_depot_work_order_status(work_orders: Sequence[dict[str, Any]]) -> dict[str, bool]:
    statuses = [work_order.get("工作單狀態") for work_order in work_orders]
    return {
        "All Depot Maintenance Work Orders Closed": bool(statuses) and all(
            status == "工單結案" for status in statuses
        ),
        "Depot Maintenance Work Orders Pending Approval": any(
            status in {"簽核中", "核簽中"} for status in statuses
        ) and all(status in {"簽核中", "核簽中", "工單結案"} for status in statuses),
    }


def execute(
    args: Sequence[str], *, include_analysis_materials: bool = True
) -> dict[str, Any]:
    options = _parse_args(args)
    notice = normalize_fault_notice(options.通報號)
    client = MMISSession(MMISConfig.from_env())
    client.login()
    result = FaultNoticeFullDetailReader(client).run(notice)
    status_checks = {
        "Sufficient Data for Fault Analysis": None,
        "Fault Analysis Completed": _fault_analysis_completed(result["故障分析"]),
        **evaluate_depot_work_order_status(result["段修工單"]),
        "CA Repair Work Orders Not Closed": any(
            not work_order.get("狀態判定") for work_order in result.get("CA查修工單", [])
        ),
        "ATP Fault Analysis Incomplete": _atp_fault_analysis_incomplete(
            result["是ATP故障"], result.get("ATP故障分析")
        ),
    }
    items = list(result.items())
    atp_index = next(index for index, (key, _) in enumerate(items) if key == "是ATP故障")
    items.insert(atp_index + 1, ("結案狀態檢查", status_checks))
    result = dict(items)
    if include_analysis_materials or options.check_analysis_readiness or options.ai_analysis:
        result["故障分析素材"] = collect_analysis_materials(client, result["段修工單"])
    if options.check_analysis_readiness:
        status_checks["Sufficient Data for Fault Analysis"] = check_analysis_readiness(result)
    if options.ai_analysis:
        result = merge_fault_analysis(result, analyze_fault_notice(result))
        if result["是ATP故障"] is True:
            try:
                suggestion = analyze_atp_fault(result)
            except MMISClientError as exc:
                analysis = result.pop("故障分析")
                result["ATP故障分析_AI建議錯誤"] = str(exc)
                result["故障分析"] = analysis
            else:
                analysis = result.pop("故障分析")
                result["ATP故障分析_AI建議"] = suggestion
                result["故障分析"] = analysis
    return result


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
