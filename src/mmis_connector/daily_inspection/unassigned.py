from __future__ import annotations

from typing import Any

from ..auth import MMISClientError
from ..parser import parse_maximo_page_info, parse_maximo_table, parse_maximo_table_schema
from .query import DEPOT, DailyInspectionWorkOrderQuery

FIELDS = ("車組/車號", "工作單", "預計檢修(進廠)日")
STATUS = "執行中未派工"
HEADERS = {*FIELDS, "配屬段", "工作單狀態"}


class UnassignedDailyInspectionWorkOrderQuery(DailyInspectionWorkOrderQuery):
    def run(self) -> list[dict[str, str]]:
        state, app_response = self.events.load_app_with_response(
            app_value="ZZ_PMWO1A", favorite_focus="FavoriteApp_ZZ_PMWO1A",
            expected_app_id="zz_pmwo1a", display_name="動力車日檢(1A)",
        )
        schema = parse_maximo_table_schema(app_response, required_headers=HEADERS)
        prefix = schema.prefix
        for sequence, (column, value, focus) in enumerate(
            ((2, DEPOT, 8), (8, STATUS, 7)), start=2
        ):
            self._post_event(
                state=self.client.state or state,
                current_focus=f"{prefix}_tfrow_[C:{focus}]_txt-tb",
                event_type="setvalue", target_id=f"{prefix}_tfrow_[C:{column}]_txt-tb",
                value=value, xhr_seq=sequence,
            )
        response = self._post_event(
            state=self.client.state or state,
            current_focus=f"{prefix}_tfrow_[C:7]_txt-tb",
            event_type="filterrows", target_id=f"{prefix}_tbod_tfrow-tr",
            value="", xhr_seq=4,
        )
        records: list[dict[str, str]] = []
        seen: set[str] = set()
        expected_start = 1
        expected_total: int | None = None
        sequence = 5
        while True:
            page_schema, rows = parse_maximo_table(response, required_headers=HEADERS)
            if page_schema is None:
                if records or "沒有要顯示的列" not in response:
                    raise MMISClientError("未派工日檢工單回應缺少表格")
                break
            page = parse_maximo_page_info(
                response, table_prefix=page_schema.prefix, context_name="未派工日檢工單"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("未派工日檢工單分頁總筆數不一致")
            if page.total == 0:
                if rows:
                    raise MMISClientError("未派工日檢工單空頁含資料")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("未派工日檢工單分頁範圍不一致")
            for row in rows:
                order = str(row["工作單"]).strip()
                if not order or order in seen or row["配屬段"] != DEPOT or row["工作單狀態"] != STATUS:
                    raise MMISClientError("未派工日檢工單資料不符合查詢條件")
                seen.add(order)
                records.append({field: str(row[field]).strip() for field in FIELDS})
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("未派工日檢工單末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("未派工日檢工單缺少下一頁")
            expected_start = page.end + 1
            response = self._post_event(
                state=self.client.state or state,
                current_focus=page.next_page_target, event_type="click",
                target_id=page.next_page_target, value="", xhr_seq=sequence,
            )
            sequence += 1
        if expected_total is not None and len(records) != expected_total:
            raise MMISClientError("未派工日檢工單擷取筆數不符")
        return records
