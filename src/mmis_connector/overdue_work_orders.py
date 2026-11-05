from __future__ import annotations

from .auth import MMISClientError, MMISSession
from .events import MaximoEventClient
from .parser import parse_maximo_page_info, parse_maximo_table

FIELDS = (
    "車組(輛)", "檢修級別", "工單編號", "工單狀態", "人員",
    "檢修日期", "完工日期", "逾期天數",
)


class OverdueWorkOrderQuery:
    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.events = MaximoEventClient(client)

    def run(self) -> list[dict[str, str]]:
        state, response = self.events.load_app_with_response(
            app_value="ZZ_WO_OVERDUE",
            favorite_focus="FavoriteApp_ZZ_WO_OVERDUE",
            expected_app_id="zz_wo_overdue",
            display_name="工單逾期查詢",
        )
        records: list[dict[str, str]] = []
        seen: set[str] = set()
        expected_start = 1
        expected_total: int | None = None
        sequence = 2
        while True:
            schema, rows = parse_maximo_table(response, required_headers=set(FIELDS))
            if schema is None:
                if records or "沒有要顯示的列" not in response:
                    raise MMISClientError("工單逾期查詢回應缺少表格")
                break
            page = parse_maximo_page_info(
                response, table_prefix=schema.prefix, context_name="工單逾期查詢"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("逾期工單分頁總筆數不一致")
            if page.total == 0:
                if rows:
                    raise MMISClientError("逾期工單空頁含有資料")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("逾期工單分頁範圍與資料不一致")
            for row in rows:
                order = str(row["工單編號"]).strip()
                if not order or order in seen:
                    raise MMISClientError("逾期工單編號缺失或重複")
                seen.add(order)
                records.append({field: str(row[field]).strip() for field in FIELDS})
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("逾期工單末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("逾期工單尚未讀完但找不到下一頁")
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
        if expected_total is not None and len(records) != expected_total:
            raise MMISClientError("逾期工單擷取筆數與總筆數不一致")
        return records
