from __future__ import annotations

import re
from typing import Any

from .auth import MMISClientError, MMISSession, PageState
from .parser import (
    parse_fault_notice_link_controls,
    parse_maximo_table,
    parse_maximo_table_schema,
)
from .query_daily_inspection_work_orders_by_vehicle_and_date import (
    REQUIRED_HEADERS,
)
from .query_fault_notices_linked_to_daily_inspection_work_order_by_number import (
    FAULT_HEADERS,
    FAULT_TABLE_SUMMARY,
    DailyInspectionWorkOrderDetailReader,
)


OPERATION_NAME = "以工作單號查詢日檢工單並勾稽故障通報"
FAULT_NOTICE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,19}$")


def normalize_fault_notice(value: str) -> str:
    fault_notice = value.strip()
    if FAULT_NOTICE_RE.fullmatch(fault_notice) is None:
        raise MMISClientError(
            "故障通報號須為 1 至 20 個英數字或連字號，且首字元須為英數字"
        )
    return fault_notice


class DailyInspectionWorkOrderFaultNoticeLinker:
    """Link one fault notice to one exact daily-inspection work order."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.detail_reader = DailyInspectionWorkOrderDetailReader(client)
        self.events = self.detail_reader.events

    def _current_state(self) -> PageState:
        if self.client.state is None:
            raise MMISClientError("MMIS 回應缺少目前頁面狀態")
        return self.client.state

    def run(self, work_order: str, fault_notice: str) -> dict[str, Any]:
        normalized_fault_notice = normalize_fault_notice(fault_notice)
        normalized_work_order, detail_response = self.detail_reader.open_detail(
            work_order
        )
        controls = parse_fault_notice_link_controls(detail_response)

        try:
            link_response = self.events.post_events(
                state=self._current_state(),
                current_focus=controls.button_target,
                events=[
                    ("setvalue", controls.input_target, normalized_fault_notice),
                    ("click", controls.button_target, ""),
                ],
                xhr_seq=6,
            )
        except MMISClientError as exc:
            raise MMISClientError(
                "故障通報勾稽結果不明，需人工確認；程式未自動重送"
            ) from exc

        try:
            _, fault_notices = parse_maximo_table(
                link_response,
                required_headers=FAULT_HEADERS,
                table_summary=FAULT_TABLE_SUMMARY,
                normalize_line_breaks=True,
            )
        except MMISClientError as exc:
            raise MMISClientError("勾稽後無法確認指定故障通報") from exc
        if not any(
            record.get("故障通報號") == normalized_fault_notice
            for record in fault_notices
        ):
            raise MMISClientError("勾稽後無法確認指定故障通報")

        try:
            list_response = self.events.post(
                state=self._current_state(),
                current_focus=controls.list_target,
                event_type="click",
                target_id=controls.list_target,
                value="",
                xhr_seq=7,
            )
            parse_maximo_table_schema(
                list_response,
                required_headers=REQUIRED_HEADERS,
            )
        except MMISClientError as exc:
            raise MMISClientError(
                "故障通報勾稽已確認，但返回清單失敗"
            ) from exc

        return {
            "success": True,
            "operation_name": OPERATION_NAME,
            "work_order": normalized_work_order,
            "fault_notice": normalized_fault_notice,
            "linked": True,
            "returned_to_list": True,
        }
