from __future__ import annotations

from typing import Any

from ..auth import MMISClientError, MMISSession
from ..daily_inspection.reader import normalize_work_order
from ..events import MaximoEventClient
from ..parser import parse_maximo_page_info, parse_maximo_table, parse_maximo_table_schema


FIELDS = ("車組/車號", "檢修級別", "工作單", "檢修單位", "工作單狀態")
REQUIRED_HEADERS = {*FIELDS, "母工單"}


class CompletePeriodicInspectionWorkOrderStatusQuery:
    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.events = MaximoEventClient(client)

    def run(self, work_order: str) -> dict[str, Any]:
        number = normalize_work_order(work_order)
        state, _ = self.events.load_app_with_response(
            app_value="ZZ_PMWO",
            favorite_focus="FavoriteApp_ZZ_PMWO",
            expected_app_id="zz_pmwo",
            display_name="定期檢修工單",
        )
        menu = self.events.post(
            state=self.client.state or state,
            current_focus="toolbar2_tbs_0_tbcb_0_query-tb",
            event_type="click",
            target_id="toolbar2_tbs_0_tbcb_0_query-img",
            value="",
            xhr_seq=1,
        )
        if "mainrec_menus" not in menu:
            raise MMISClientError("MMIS 未回傳定期檢修工單查詢選單")
        response = self.events.post(
            state=self.client.state or state,
            current_focus="menu0_useAllRecsQuery_OPTION_a",
            event_type="click",
            target_id="mainrec_menus",
            value="useAllRecsQuery_OPTION",
            xhr_seq=2,
        )
        schema = parse_maximo_table_schema(response, required_headers=REQUIRED_HEADERS)
        columns = {label: column for column, label in schema.headers.items()}
        for sequence, (field, value) in enumerate(
            (("工作單", number), ("母工單", "0")), start=3
        ):
            target = f"{schema.prefix}_tfrow_[C:{columns[field]}]_txt-tb"
            self.events.post(
                state=self.client.state or state,
                current_focus=target,
                event_type="setvalue",
                target_id=target,
                value=value,
                xhr_seq=sequence,
            )
        work_target = f"{schema.prefix}_tfrow_[C:{columns['工作單']}]_txt-tb"
        response = self.events.post(
            state=self.client.state or state,
            current_focus=work_target,
            event_type="filterrows",
            target_id=f"{schema.prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=5,
        )

        records: list[dict[str, str]] = []
        seen: set[str] = set()
        expected_start = 1
        expected_total: int | None = None
        sequence = 6
        while True:
            page_schema = parse_maximo_table_schema(response, required_headers=REQUIRED_HEADERS)
            if page_schema.prefix != schema.prefix:
                raise MMISClientError("定期檢修工單結果表格已變更")
            _, rows = parse_maximo_table(response, required_headers=REQUIRED_HEADERS)
            page = parse_maximo_page_info(
                response, table_prefix=schema.prefix, context_name="定期檢修工單"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("定期檢修工單分頁總筆數不一致")
            if page.total == 0:
                if rows or page.start or page.end or page.next_page_target:
                    raise MMISClientError("定期檢修工單空頁與表格資料不一致")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("定期檢修工單分頁範圍與資料不一致")
            for row in rows:
                record = {field: str(row[field]).strip() for field in FIELDS}
                child_number = record["工作單"]
                if (
                    not child_number.startswith(f"{number}-")
                    or not child_number[len(number) + 1 :].isdigit()
                    or str(row["母工單"]).strip() != "0"
                    or child_number in seen
                ):
                    raise MMISClientError("定期檢修工單結果與查詢條件不符或重複")
                seen.add(child_number)
                records.append(record)
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("定期檢修工單末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("定期檢修工單尚未讀完但找不到下一頁")
            expected_start = page.end + 1
            response = self.events.post(
                state=self.client.state or state,
                current_focus=page.next_page_target,
                event_type="click",
                target_id=page.next_page_target,
                value="",
                xhr_seq=sequence,
            )
            sequence += 1
        if len(records) != expected_total:
            raise MMISClientError("定期檢修工單擷取筆數與總筆數不一致")
        return {
            "success": True,
            "query_name": "查詢完整定期檢修工單狀態",
            "work_order": number,
            "count": len(records),
            "records": records,
        }
