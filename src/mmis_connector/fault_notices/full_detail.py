from __future__ import annotations

from typing import Any

from ..parser import (
    parse_atp_fault_checked,
    parse_fault_notice_basic_info,
    parse_labeled_inputs,
    parse_labeled_textareas,
    parse_maximo_tab_target,
)
from .atp_reader import ATP_ANALYSIS_FIELDS
from .linked_work_orders import LinkedWorkOrdersReader
from .reader import ANALYSIS_FIELDS, FaultNoticeAnalysisReader, normalize_fault_notice
from .repair_work_orders import RepairWorkOrdersReader


class FaultNoticeFullDetailReader(FaultNoticeAnalysisReader):
    """Read one fault notice and its related data through one MMIS session."""

    def run(self, fault_notice: str) -> dict[str, Any]:
        notice = normalize_fault_notice(fault_notice)
        state, detail_response = self._load_exact_detail(notice)
        basic_info = parse_fault_notice_basic_info(
            detail_response, expected_notice=notice
        )
        atp_checked = parse_atp_fault_checked(detail_response)

        tracking_tab = parse_maximo_tab_target(detail_response, title="故障追蹤")
        tracking_response = self._post_event(
            state=self.client.state or state,
            current_focus=tracking_tab,
            event_type="click",
            target_id=tracking_tab,
            value="",
            xhr_seq=3,
        )
        linked_reader = LinkedWorkOrdersReader(self.client)
        repair_reader = RepairWorkOrdersReader(self.client)
        work_orders, xhr_seq = linked_reader.read_records(
            tracking_response, state=state, xhr_seq=4
        )
        repair_orders, xhr_seq = repair_reader.read_records(
            tracking_response, state=state, xhr_seq=xhr_seq
        )

        analysis_tab = parse_maximo_tab_target(detail_response, title="故障分析")
        analysis_response = self._post_event(
            state=self.client.state or state,
            current_focus=analysis_tab,
            event_type="click",
            target_id=analysis_tab,
            value="",
            xhr_seq=xhr_seq,
        )
        analysis = parse_labeled_textareas(
            analysis_response, field_names=ANALYSIS_FIELDS
        )
        atp_analysis = None
        if atp_checked:
            atp_tab = parse_maximo_tab_target(
                analysis_response, title="故障分析-ATP"
            )
            atp_response = self._post_event(
                state=self.client.state or state,
                current_focus=atp_tab,
                event_type="click",
                target_id=atp_tab,
                value="",
                xhr_seq=xhr_seq + 1,
            )
            atp_analysis = parse_labeled_inputs(
                atp_response,
                field_names=ATP_ANALYSIS_FIELDS,
                context_name="ATP故障分析",
            )

        return {
            **basic_info,
            "是ATP故障": atp_checked,
            "段修工單": work_orders,
            "CA查修工單": repair_orders,
            "故障分析": analysis,
            "ATP故障分析": atp_analysis,
        }
