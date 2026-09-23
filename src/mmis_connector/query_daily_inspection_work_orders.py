from __future__ import annotations

from datetime import datetime
from typing import Any

from .auth import MMISClientError, MMISSession, PageState
from .events import MaximoEventClient
from .parser import (
    parse_maximo_page_info,
    parse_maximo_table,
    parse_maximo_table_schema,
)


QUERY_NAME = "查詢日檢工單"
DEPOT = "新竹機務段"
REQUIRED_HEADERS = {"檢修段", "車組/車號", "工作單", "檢修日期"}


def normalize_vehicle(value: str) -> str:
    vehicle = value.strip()
    if not vehicle:
        raise MMISClientError("車組/車號不得為空白")
    return vehicle


def normalize_inspection_date(value: str) -> str:
    raw = value.strip()
    if raw.startswith(">"):
        raw = raw[1:].strip()
    try:
        parsed = datetime.strptime(raw, "%Y/%m/%d")
    except ValueError as exc:
        raise MMISClientError("檢修日期必須是有效的 YYYY/MM/DD 日期") from exc
    return parsed.strftime("%Y/%m/%d")


class DailyInspectionWorkOrderQuery:
    """Query 動力車日檢(1A) work orders without a browser."""

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

    def _load_app(self) -> PageState:
        return self.events.load_app(
            app_value="ZZ_PMWO1A",
            favorite_focus="FavoriteApp_ZZ_PMWO1A",
            expected_app_id="zz_pmwo1a",
            display_name="動力車日檢(1A)",
        )

    def run(self, vehicle: str, inspection_date: str) -> dict[str, Any]:
        normalized_vehicle = normalize_vehicle(vehicle)
        normalized_date = normalize_inspection_date(inspection_date)
        state = self._load_app()

        menu_response = self._post_event(
            state=state,
            current_focus="toolbar2_tbs_0_tbcb_0_query-tb",
            event_type="click",
            target_id="toolbar2_tbs_0_tbcb_0_query-img",
            value="",
            xhr_seq=1,
        )
        if "mainrec_menus" not in menu_response:
            raise MMISClientError("MMIS 未回傳日檢工單查詢選單")

        all_records_response = self._post_event(
            state=self.client.state or state,
            current_focus="menu0_useAllRecsQuery_OPTION_a",
            event_type="click",
            target_id="mainrec_menus",
            value="useAllRecsQuery_OPTION",
            xhr_seq=2,
        )
        schema = parse_maximo_table_schema(
            all_records_response, required_headers=REQUIRED_HEADERS
        )
        prefix = schema.prefix
        values = (
            (1, DEPOT, 3),
            (3, normalized_vehicle, 11),
            (11, f">{normalized_date}", 10),
        )
        for xhr_seq, (column, value, focus_column) in enumerate(values, start=3):
            self._post_event(
                state=self.client.state or state,
                current_focus=f"{prefix}_tfrow_[C:{focus_column}]_txt-tb",
                event_type="setvalue",
                target_id=f"{prefix}_tfrow_[C:{column}]_txt-tb",
                value=value,
                xhr_seq=xhr_seq,
            )

        result_response = self._post_event(
            state=self.client.state or state,
            current_focus=f"{prefix}_tfrow_[C:10]_txt-tb",
            event_type="filterrows",
            target_id=f"{prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=6,
        )
        result_schema, records = parse_maximo_table(
            result_response,
            required_headers=REQUIRED_HEADERS,
            checkbox_headers={"逾期標註?"},
        )
        if result_schema is not None:
            page_info = parse_maximo_page_info(
                result_response,
                table_prefix=result_schema.prefix,
                context_name="日檢工單",
            )
            if page_info.total != len(records) or page_info.next_page_target is not None:
                raise MMISClientError("日檢工單結果超過單頁，拒絕回傳不完整資料")

        result: dict[str, Any] = {
            "success": True,
            "query_name": QUERY_NAME,
            "vehicle": normalized_vehicle,
            "inspection_date": normalized_date,
            "count": len(records),
            "records": records,
        }
        if not records:
            result["message"] = "找不到對應工單"
        return result
