from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..auth import MMISClientError
from ..parser import parse_maximo_page_info, parse_maximo_table, parse_maximo_table_schema
from .query import DEPOT, DailyInspectionWorkOrderQuery


FIELDS = (
    "檢修段", "配屬段", "車組/車號", "檢修級別", "工作單", "車次",
    "檢修單位", "工作單狀態", "處理人員", "預計檢修(進廠)日",
    "檢修日期", "完工日期", "階段核簽人", "逾期標註",
)
TABLE_HEADERS = set(FIELDS[:-1]) | {"逾期標註?"}
STATUSES = (
    "執行中已派工", "執行中未派工", "完工待回報", "工單初始", "工單取消",
    "工單取消核簽中", "工單取消申請", "工單結案", "工單退回", "檢修完成",
)
STATUS_FILTER = ",".join(STATUSES)


class DailyInspectionNotSubmittedQuery(DailyInspectionWorkOrderQuery):
    """Read every 1A work order awaiting submission for approval."""

    def run(self, *, today: datetime | None = None) -> dict[str, Any]:
        current_date = (today or datetime.now(ZoneInfo("Asia/Taipei"))).date()
        query_date = current_date.strftime("%Y/%m/%d")
        state, app_response = self.events.load_app_with_response(
            app_value="ZZ_PMWO1A",
            favorite_focus="FavoriteApp_ZZ_PMWO1A",
            expected_app_id="zz_pmwo1a",
            display_name="動力車日檢(1A)",
        )
        schema = parse_maximo_table_schema(app_response, required_headers=TABLE_HEADERS)
        prefix = schema.prefix
        for xhr_seq, (column, value, focus_column) in enumerate(
            (
                (1, DEPOT, 2),
                (2, "", 11),
                (11, f"<{query_date}", 8),
                (8, STATUS_FILTER, 7),
            ), start=2
        ):
            self._post_event(
                state=self.client.state or state,
                current_focus=f"{prefix}_tfrow_[C:{focus_column}]_txt-tb",
                event_type="setvalue",
                target_id=f"{prefix}_tfrow_[C:{column}]_txt-tb",
                value=value,
                xhr_seq=xhr_seq,
            )
        response = self._post_event(
            state=self.client.state or state,
            current_focus=f"{prefix}_tfrow_[C:7]_txt-tb",
            event_type="filterrows",
            target_id=f"{prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=6,
        )

        records: list[dict[str, Any]] = []
        seen_work_orders: set[str] = set()
        expected_start = 1
        expected_total: int | None = None
        xhr_seq = 7
        while True:
            page_schema, rows = parse_maximo_table(
                response, required_headers=TABLE_HEADERS,
                checkbox_headers={"逾期標註?"},
            )
            if page_schema is None:
                if records or "沒有要顯示的列" not in response:
                    raise MMISClientError("日檢工單回應缺少表格結構")
                break
            page = parse_maximo_page_info(
                response, table_prefix=page_schema.prefix, context_name="日檢工單"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("日檢工單分頁總筆數不一致")
            if page.total == 0:
                if rows:
                    raise MMISClientError("日檢工單空頁含有資料")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("日檢工單分頁範圍與資料不一致")
            for row in rows:
                work_order = str(row["工作單"]).strip()
                if not work_order:
                    raise MMISClientError("日檢工單資料缺少工作單")
                if work_order in seen_work_orders:
                    raise MMISClientError("日檢工單分頁出現重複工作單")
                try:
                    inspection_date = datetime.strptime(
                        str(row["檢修日期"]), "%Y/%m/%d"
                    ).date()
                except ValueError as exc:
                    raise MMISClientError("日檢工單檢修日期格式無效") from exc
                if (
                    row["檢修段"] != DEPOT
                    or row["工作單狀態"] not in STATUSES
                    or inspection_date >= current_date
                ):
                    raise MMISClientError("日檢工單資料不符合查詢條件")
                seen_work_orders.add(work_order)
                record = {field: row[field] for field in FIELDS[:-1]}
                record["逾期標註"] = row["逾期標註?"]
                records.append(record)
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("日檢工單末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("日檢工單尚未讀完但找不到下一頁")
            expected_start = page.end + 1
            response = self._post_event(
                state=self.client.state or state,
                current_focus=page.next_page_target,
                event_type="click",
                target_id=page.next_page_target,
                value="",
                xhr_seq=xhr_seq,
            )
            xhr_seq += 1

        if expected_total is not None and len(records) != expected_total:
            raise MMISClientError("日檢工單擷取筆數與總筆數不一致")
        return {
            "success": True,
            "query_name": "查詢未送簽核的日檢工單",
            "depot": DEPOT,
            "before_inspection_date": query_date,
            "status": STATUS_FILTER,
            "count": len(records),
            "records": records,
        }
