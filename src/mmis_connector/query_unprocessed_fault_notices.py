from __future__ import annotations

import html
import json
import re
from typing import Any

from .auth import MMISClientError, MMISSession, PageState, parse_page_state
from .parser import parse_fault_notice_page_info, parse_fault_notice_table


QUERY_NAME = "本段未處理通報(車輛配屬段)"
QUERY_MENU_VALUE = "本段未處理通報_query"
QUERY_FOCUS_ID = "menu0_本段未處理通報_query_a"
EVENT_REDIRECT_RE = re.compile(r"<redirect><!\[CDATA\[(?P<url>[^\]]+)\]\]></redirect>")


class UnprocessedFaultNoticeQuery:
    """Query the saved list named 本段未處理通報(車輛配屬段)."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client

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
        event = {
            "type": event_type,
            "targetId": target_id,
            "value": value,
            "requestType": "SYNC",
            "csrftokenholder": state.csrf_token,
        }
        payload = {
            "uisessionid": state.ui_session_id,
            "csrftoken": state.csrf_token,
            "currentfocus": current_focus,
            "scrollleftpos": "0",
            "localStorage": "true",
            "scrolltoppos": "0",
            "requesttype": "SYNC",
            "responsetype": "text/xml",
            "events": json.dumps([event], ensure_ascii=False, separators=(",", ":")),
        }
        response = self.client.request(
            "POST",
            self.client.event_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": self.client.config.base_url,
                "Referer": state.page_url,
                "qmtry": "1",
                "pageseqnum": str(state.page_seq),
                "xhrseqnum": str(xhr_seq),
            },
        )
        if "exit.jsp?sharedSession=1" in response.text:
            raise MMISClientError("MMIS session 拒絕 event，請重新執行")
        try:
            self.client.state = parse_page_state(response.text, state.page_url)
        except MMISClientError:
            self.client.state = state
        return response.text

    def _load_fault_notice_app(self) -> PageState:
        if self.client.state is None:
            self.client.login()
        assert self.client.state is not None
        if self.client.state.app_id != "startcntr":
            start_url = (
                f"{self.client.config.base_url}/maximo/ui/login"
                f"?uisessionid={self.client.state.ui_session_id}"
                "&event=loadapp&value=startcntr"
            )
            self.client.refresh_state(start_url)

        state, _ = self.client.refresh_state()
        response_text = self._post_event(
            state=state,
            current_focus="FavoriteApp_ZZ_FNM",
            event_type="changeapp",
            target_id="startcntr",
            value="ZZ_FNM",
            xhr_seq=1,
        )
        redirect_match = EVENT_REDIRECT_RE.search(html.unescape(response_text))
        if not redirect_match:
            raise MMISClientError("切換故障通報管理後找不到 redirect")
        app_state, _ = self.client.refresh_state(redirect_match.group("url"))
        if app_state.app_id.lower() != "zz_fnm":
            raise MMISClientError("未成功進入故障通報管理")
        return app_state

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
