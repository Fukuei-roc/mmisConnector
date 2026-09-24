from __future__ import annotations

import re
from typing import Any

from .auth import MMISClientError, MMISSession, PageState
from .parser import parse_maximo_page_info, parse_maximo_table
from .query_daily_inspection_work_orders_by_vehicle_and_date import (
    REQUIRED_HEADERS,
    DailyInspectionWorkOrderQuery,
)


QUERY_NAME = "以工作單號查詢日檢工單內容"
FAULT_TABLE_SUMMARY = "故障通報管理"
FAULT_HEADERS = {"故障通報號", "發生日期", "車組/車號", "故障現象"}
WORK_ORDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")


def normalize_work_order(value: str) -> str:
    work_order = value.strip()
    if not work_order or WORK_ORDER_RE.fullmatch(work_order) is None:
        raise MMISClientError("工作單號只能包含英數字與連字號")
    return work_order


class DailyInspectionWorkOrderDetailReader:
    """Read one 動力車日檢(1A) work order detail without a browser."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.list_query = DailyInspectionWorkOrderQuery(client)
        self.events = self.list_query.events

    def _post_event(
        self,
        *,
        state: PageState,
        current_focus: str,
        event_type: str,
        target_id: str,
        value: str,
        xhr_seq: int,
    ) -> str:
        return self.events.post(
            state=state,
            current_focus=current_focus,
            event_type=event_type,
            target_id=target_id,
            value=value,
            xhr_seq=xhr_seq,
        )

    def run(self, work_order: str) -> dict[str, Any]:
        normalized_work_order = normalize_work_order(work_order)
        state, list_schema = self.list_query.open_all_records()
        prefix = list_schema.prefix

        self._post_event(
            state=self.client.state or state,
            current_focus=f"{prefix}_tfrow_[C:5]_txt-tb",
            event_type="setvalue",
            target_id=f"{prefix}_tfrow_[C:5]_txt-tb",
            value=normalized_work_order,
            xhr_seq=3,
        )
        result_response = self._post_event(
            state=self.client.state or state,
            current_focus=f"{prefix}_tfrow_[C:5]_txt-tb",
            event_type="filterrows",
            target_id=f"{prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=4,
        )
        result_schema, work_orders = parse_maximo_table(
            result_response,
            required_headers=REQUIRED_HEADERS,
            checkbox_headers={"逾期標註?"},
        )
        if not work_orders:
            raise MMISClientError(f"找不到工作單：{normalized_work_order}")
        if result_schema is None or len(work_orders) != 1:
            raise MMISClientError("工作單查詢結果不是唯一一筆")
        if work_orders[0].get("工作單") != normalized_work_order:
            raise MMISClientError("工作單查詢結果與輸入不相符")

        page_info = parse_maximo_page_info(
            result_response,
            table_prefix=result_schema.prefix,
            context_name="日檢工單",
        )
        if page_info.total != 1 or page_info.next_page_target is not None:
            raise MMISClientError("工作單查詢結果不是唯一一筆")

        work_order_column = next(
            column
            for column, label in result_schema.headers.items()
            if label == "工作單"
        )
        detail_target = (
            f"{result_schema.prefix}_tdrow_[C:{work_order_column}]"
            "_ttxt-lb[R:0]"
        )
        detail_response = self._post_event(
            state=self.client.state or state,
            current_focus=detail_target,
            event_type="click",
            target_id=detail_target,
            value="",
            xhr_seq=5,
        )
        fault_schema, fault_notices = parse_maximo_table(
            detail_response,
            required_headers=FAULT_HEADERS,
            table_summary=FAULT_TABLE_SUMMARY,
            normalize_line_breaks=True,
        )
        if fault_schema is None:
            raise MMISClientError("查詢回應找不到故障通報管理表格")
        if fault_notices:
            fault_page = parse_maximo_page_info(
                detail_response,
                table_prefix=fault_schema.prefix,
                context_name=FAULT_TABLE_SUMMARY,
            )
            if (
                fault_page.total != len(fault_notices)
                or fault_page.next_page_target is not None
            ):
                raise MMISClientError(
                    "故障通報管理結果超過單頁，拒絕回傳不完整資料"
                )

        return {
            "success": True,
            "query_name": QUERY_NAME,
            "work_order": normalized_work_order,
            "has_fault_notices": bool(fault_notices),
            "count": len(fault_notices),
            "records": fault_notices,
        }
