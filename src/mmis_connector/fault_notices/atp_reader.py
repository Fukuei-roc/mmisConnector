from __future__ import annotations

from typing import Any

from ..auth import MMISClientError
from ..parser import (
    parse_atp_fault_checked,
    parse_labeled_inputs,
    parse_maximo_tab_target,
)
from .reader import FaultNoticeAnalysisReader, normalize_fault_notice


QUERY_NAME = "查詢故障通報關聯的ATP故障分析"
ATP_ANALYSIS_FIELDS = (
    "故障要因",
    "故障因子",
    "故障項目",
)


class FaultNoticeATPAnalysisReader(FaultNoticeAnalysisReader):
    """Read the ATP analysis for an exactly matched fault notice via HTTP."""

    def run(self, fault_notice: str) -> dict[str, Any]:
        normalized_notice = normalize_fault_notice(fault_notice)
        state, detail_response = self._load_exact_detail(normalized_notice)
        if not parse_atp_fault_checked(detail_response):
            raise MMISClientError("此故障通報未勾選ATP故障")

        analysis_tab = parse_maximo_tab_target(detail_response, title="故障分析")
        analysis_response = self.events.post(
            state=self.client.state or state,
            current_focus=analysis_tab,
            event_type="click",
            target_id=analysis_tab,
            value="",
            xhr_seq=3,
        )
        atp_tab = parse_maximo_tab_target(
            analysis_response, title="故障分析-ATP"
        )
        atp_response = self.events.post(
            state=self.client.state or state,
            current_focus=atp_tab,
            event_type="click",
            target_id=atp_tab,
            value="",
            xhr_seq=4,
        )
        analysis = parse_labeled_inputs(
            atp_response,
            field_names=ATP_ANALYSIS_FIELDS,
            context_name="ATP故障分析",
        )
        return {
            "success": True,
            "query_name": QUERY_NAME,
            "fault_notice": normalized_notice,
            "analysis": analysis,
        }
