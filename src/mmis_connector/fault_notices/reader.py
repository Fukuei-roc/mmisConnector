from __future__ import annotations

import re
from typing import Any

from ..auth import MMISClientError, MMISSession, PageState
from ..events import MaximoEventClient
from ..parser import (
    parse_labeled_textareas,
    parse_maximo_page_info,
    parse_maximo_tab_target,
    parse_maximo_table,
    parse_maximo_table_schema,
)


QUERY_NAME = "查詢故障通報的故障分析"
REQUIRED_HEADERS = {"通報號"}
ANALYSIS_FIELDS = (
    "事故現象",
    "處理概況",
    "故障原因",
    "處理情形",
    "改善對策",
)
FAULT_NOTICE_RE = re.compile(r"^\d{7}-\d{2}$")


def normalize_fault_notice(value: str) -> str:
    fault_notice = value.strip()
    if FAULT_NOTICE_RE.fullmatch(fault_notice) is None:
        raise MMISClientError("通報號必須符合 7 位數字-兩位數字格式")
    return fault_notice


class FaultNoticeAnalysisReader:
    """Read the five fault-analysis fields for one exact fault notice."""

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

    def _load_list(self) -> tuple[PageState, str]:
        state = self.events.load_app(
            app_value="ZZ_FNM",
            favorite_focus="FavoriteApp_ZZ_FNM",
            expected_app_id="zz_fnm",
            display_name="故障通報管理",
        )
        return self.client.refresh_state(state.page_url)

    def run(self, fault_notice: str) -> dict[str, Any]:
        normalized_notice = normalize_fault_notice(fault_notice)
        state, list_response = self._load_list()
        list_schema = parse_maximo_table_schema(
            list_response, required_headers=REQUIRED_HEADERS
        )
        notice_columns = [
            column
            for column, header in list_schema.headers.items()
            if header == "通報號"
        ]
        if len(notice_columns) != 1:
            raise MMISClientError("故障通報清單找不到唯一的「通報號」欄位")
        notice_column = notice_columns[0]
        filter_target = (
            f"{list_schema.prefix}_tfrow_[C:{notice_column}]_txt-tb"
        )
        filter_response = self.events.post_events(
            state=self.client.state or state,
            current_focus=filter_target,
            events=[
                ("setvalue", filter_target, normalized_notice),
                ("filterrows", f"{list_schema.prefix}_tbod_tfrow-tr", ""),
            ],
            xhr_seq=1,
        )
        result_schema, records = parse_maximo_table(
            filter_response, required_headers=REQUIRED_HEADERS
        )
        if not records:
            raise MMISClientError(f"找不到故障通報：{normalized_notice}")
        if result_schema is None or len(records) != 1:
            raise MMISClientError("故障通報查詢結果不是唯一一筆")
        if records[0].get("通報號") != normalized_notice:
            raise MMISClientError("故障通報查詢結果與輸入不相符")
        result_notice_columns = [
            column
            for column, header in result_schema.headers.items()
            if header == "通報號"
        ]
        if len(result_notice_columns) != 1:
            raise MMISClientError("故障通報結果找不到唯一的「通報號」欄位")
        page_info = parse_maximo_page_info(
            filter_response,
            table_prefix=result_schema.prefix,
            context_name="故障通報",
        )
        if page_info.total != 1 or page_info.next_page_target is not None:
            raise MMISClientError("故障通報查詢結果不是唯一一筆")

        detail_target = (
            f"{result_schema.prefix}_tdrow_[C:{result_notice_columns[0]}]"
            "_ttxt-lb[R:0]"
        )
        detail_response = self._post_event(
            state=self.client.state or state,
            current_focus=detail_target,
            event_type="click",
            target_id=detail_target,
            value="",
            xhr_seq=2,
        )
        analysis_tab = parse_maximo_tab_target(
            detail_response, title="故障分析"
        )
        analysis_response = self._post_event(
            state=self.client.state or state,
            current_focus=analysis_tab,
            event_type="click",
            target_id=analysis_tab,
            value="",
            xhr_seq=3,
        )
        analysis = parse_labeled_textareas(
            analysis_response, field_names=ANALYSIS_FIELDS
        )
        return {
            "success": True,
            "query_name": QUERY_NAME,
            "fault_notice": normalized_notice,
            "analysis": analysis,
        }
