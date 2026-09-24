from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from .auth import MMISClientError, MMISSession, PageState
from .events import MaximoEventClient
from .parser import (
    FaultNoticePageInfo,
    parse_fault_notice_page_info,
    parse_fault_notice_table,
)


QUERY_NAME = "本段未處理通報(車輛配屬段)"
QUERY_MENU_VALUE = "本段未處理通報_query"
QUERY_FOCUS_ID = "menu0_本段未處理通報_query_a"
SECONDARY_QUERY_NAME = "本段未處理通報(開單時所屬段)"
SECONDARY_QUERY_MENU_VALUE = "本段未處理通報(開單時所屬段)_query"
SECONDARY_QUERY_FOCUS_ID = "menu0_本段未處理通報(開單時所屬段)_query_a"


@dataclass(frozen=True)
class _SavedQuery:
    name: str
    menu_value: str
    focus_id: str


PRIMARY_QUERY = _SavedQuery(QUERY_NAME, QUERY_MENU_VALUE, QUERY_FOCUS_ID)
SECONDARY_QUERY = _SavedQuery(
    SECONDARY_QUERY_NAME,
    SECONDARY_QUERY_MENU_VALUE,
    SECONDARY_QUERY_FOCUS_ID,
)


class UnprocessedFaultNoticeQuery:
    """Select the larger unprocessed-fault saved query and return all its rows."""

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

    def _select_saved_query(
        self,
        *,
        state: PageState,
        query: _SavedQuery,
        xhr_seq: int,
    ) -> tuple[str, int]:
        menu_response = self._post_event(
            state=self.client.state or state,
            current_focus="toolbar2_tbs_0_tbcb_0_query-tb",
            event_type="click",
            target_id="toolbar2_tbs_0_tbcb_0_query-img",
            value="",
            xhr_seq=xhr_seq,
        )
        if "mainrec_menus" not in menu_response:
            raise MMISClientError("MMIS 未回傳儲存查詢選單")

        query_response = self._post_event(
            state=self.client.state or state,
            current_focus=query.focus_id,
            event_type="click",
            target_id="mainrec_menus",
            value=query.menu_value,
            xhr_seq=xhr_seq + 1,
        )
        if query.name not in html.unescape(query_response):
            raise MMISClientError("MMIS 未確認已套用指定儲存查詢")
        return query_response, xhr_seq + 2

    @staticmethod
    def _validate_page_size(
        records: list[dict[str, Any]], page_info: FaultNoticePageInfo
    ) -> None:
        expected_size = (
            0 if page_info.total == 0 else page_info.end - page_info.start + 1
        )
        if len(records) != expected_size:
            raise MMISClientError("故障通報當頁筆數與分頁範圍不符")

    def _collect_selected_query(
        self,
        *,
        state: PageState,
        first_response: str,
        xhr_seq: int,
    ) -> list[dict[str, Any]]:
        records = parse_fault_notice_table(first_response)
        page_info = parse_fault_notice_page_info(first_response)
        self._validate_page_size(records, page_info)

        expected_total = page_info.total
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
            self._validate_page_size(next_records, next_page_info)
            records.extend(next_records)
            page_info = next_page_info
            xhr_seq += 1

        if len(records) != expected_total:
            raise MMISClientError("故障通報擷取筆數與總筆數不符")
        return records

    def run(self) -> dict[str, Any]:
        state = self._load_fault_notice_app()
        xhr_seq = 1

        primary_response, xhr_seq = self._select_saved_query(
            state=state,
            query=PRIMARY_QUERY,
            xhr_seq=xhr_seq,
        )
        primary_total = parse_fault_notice_page_info(primary_response).total

        secondary_response, xhr_seq = self._select_saved_query(
            state=state,
            query=SECONDARY_QUERY,
            xhr_seq=xhr_seq,
        )
        secondary_total = parse_fault_notice_page_info(secondary_response).total

        if primary_total >= secondary_total:
            selected_query = PRIMARY_QUERY
            selected_response, xhr_seq = self._select_saved_query(
                state=state,
                query=selected_query,
                xhr_seq=xhr_seq,
            )
        else:
            selected_query = SECONDARY_QUERY
            selected_response = secondary_response

        records = self._collect_selected_query(
            state=state,
            first_response=selected_response,
            xhr_seq=xhr_seq,
        )
        return {
            "success": True,
            "query_name": selected_query.name,
            "count": len(records),
            "records": records,
        }
