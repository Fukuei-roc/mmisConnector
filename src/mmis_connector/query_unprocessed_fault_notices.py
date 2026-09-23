from __future__ import annotations

import html
from typing import Any

from .auth import MMISClientError, MMISSession, PageState
from .events import MaximoEventClient
from .parser import parse_fault_notice_page_info, parse_fault_notice_table


QUERY_NAME = "本段未處理通報(車輛配屬段)"
QUERY_MENU_VALUE = "本段未處理通報_query"
QUERY_FOCUS_ID = "menu0_本段未處理通報_query_a"
class UnprocessedFaultNoticeQuery:
    """Query the saved list named 本段未處理通報(車輛配屬段)."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.events = MaximoEventClient(client)

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

    def _load_fault_notice_app(self) -> PageState:
        return self.events.load_app(
            app_value="ZZ_FNM",
            favorite_focus="FavoriteApp_ZZ_FNM",
            expected_app_id="zz_fnm",
            display_name="故障通報管理",
        )

    def run(self) -> dict[str, Any]:
        state = self._load_fault_notice_app()
        menu_response = self._post_event(
            state=state,
            current_focus="toolbar2_tbs_0_tbcb_0_query-tb",
            event_type="click",
            target_id="toolbar2_tbs_0_tbcb_0_query-img",
            value="",
            xhr_seq=1,
        )
        if "mainrec_menus" not in menu_response:
            raise MMISClientError("MMIS 未回傳儲存查詢選單")

        query_response = self._post_event(
            state=self.client.state or state,
            current_focus=QUERY_FOCUS_ID,
            event_type="click",
            target_id="mainrec_menus",
            value=QUERY_MENU_VALUE,
            xhr_seq=2,
        )
        if QUERY_NAME not in html.unescape(query_response):
            raise MMISClientError("MMIS 未確認已套用指定儲存查詢")
        records = parse_fault_notice_table(query_response)
        page_info = parse_fault_notice_page_info(query_response)
        if len(records) != page_info.end - page_info.start + 1:
            if not (page_info.total == 0 and not records):
                raise MMISClientError("故障通報當頁筆數與分頁範圍不符")

        expected_total = page_info.total
        xhr_seq = 3
        while page_info.end < expected_total:
            if page_info.next_page_target is None:
                raise MMISClientError("故障通報尚未擷取完畢，但找不到下一頁")
            next_response = self._post_event(
                state=self.client.state or state,
                current_focus=page_info.next_page_target,
                event_type="click",
                target_id=page_info.next_page_target,
                value="true",
                xhr_seq=xhr_seq,
            )
            next_records = parse_fault_notice_table(next_response)
            next_page_info = parse_fault_notice_page_info(next_response)
            if next_page_info.total != expected_total:
                raise MMISClientError("故障通報分頁過程中總筆數改變")
            if next_page_info.start != page_info.end + 1:
                raise MMISClientError("故障通報分頁範圍不連續")
            if len(next_records) != next_page_info.end - next_page_info.start + 1:
                raise MMISClientError("故障通報當頁筆數與分頁範圍不符")
            records.extend(next_records)
            page_info = next_page_info
            xhr_seq += 1

        if len(records) != expected_total:
            raise MMISClientError("故障通報擷取筆數與總筆數不符")
        return {
            "success": True,
            "query_name": QUERY_NAME,
            "count": len(records),
            "records": records,
        }
