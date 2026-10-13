from __future__ import annotations

from typing import Any

from ..auth import MMISClientError, MMISSession
from ..daily_inspection.reader import normalize_work_order
from ..events import MaximoEventClient
from ..parser import (
    _parse_maximo_markup,
    parse_maximo_page_info,
    parse_maximo_tab_target,
    parse_maximo_table,
    parse_maximo_table_schema,
)


LIST_HEADERS = {"工作單"}
RECORD_FIELDS = ("裝置名稱", "檢修項目", "回報結果", "備註")
RECORD_HEADERS = set(RECORD_FIELDS)


class PeriodicInspectionWorkOrderDetailReader:
    """Read nonempty inspection remarks from one exact ZZ_PMWO work order."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.events = MaximoEventClient(client)

    def run(self, work_order: str) -> dict[str, Any]:
        number = normalize_work_order(work_order)
        state, response = self.events.load_app_with_response(
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
        schema = parse_maximo_table_schema(response, required_headers=LIST_HEADERS)
        columns = {label: index for index, label in schema.headers.items()}
        work_input = f"{schema.prefix}_tfrow_[C:{columns['工作單']}]_txt-tb"
        self.events.post(
            state=self.client.state or state,
            current_focus=work_input,
            event_type="setvalue",
            target_id=work_input,
            value=number,
            xhr_seq=3,
        )
        response = self.events.post(
            state=self.client.state or state,
            current_focus=work_input,
            event_type="filterrows",
            target_id=f"{schema.prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=4,
        )
        result_schema, rows = parse_maximo_table(
            response, required_headers=LIST_HEADERS
        )
        if result_schema is None:
            raise MMISClientError(f"找不到工作單：{number}")
        page = parse_maximo_page_info(
            response, table_prefix=result_schema.prefix, context_name="定期檢修工單"
        )
        if page.total == 0 and not rows:
            raise MMISClientError(f"找不到工作單：{number}")
        if (
            page.total != 1 or page.start != 1 or page.end != 1
            or page.next_page_target is not None or len(rows) != 1
            or rows[0]["工作單"] != number
        ):
            raise MMISClientError("工作單查詢結果不是唯一且完全相符的一筆")
        work_column = next(
            column for column, label in result_schema.headers.items()
            if label == "工作單"
        )
        detail_target = (
            f"{result_schema.prefix}_tdrow_[C:{work_column}]_ttxt-lb[R:0]"
        )
        detail = self.events.post(
            state=self.client.state or state,
            current_focus=detail_target,
            event_type="click",
            target_id=detail_target,
            value="",
            xhr_seq=5,
        )
        _, soup = _parse_maximo_markup(detail)
        detail_numbers = {
            str(soup.find(id=str(label["for"])).get("value", "")).strip()
            for label in soup.find_all("label", attrs={"for": True})
            if label.get_text(" ", strip=True).rstrip(":：").strip() == "工作單"
            and soup.find(id=str(label["for"])) is not None
        }
        if detail_numbers != {number}:
            raise MMISClientError("定期檢修工單明細工作單與輸入不相符")
        report_tab = parse_maximo_tab_target(detail, title="檢修回報")
        report = self.events.post(
            state=self.client.state or state,
            current_focus=report_tab,
            event_type="click",
            target_id=report_tab,
            value="",
            xhr_seq=6,
        )
        record_tab = parse_maximo_tab_target(report, title="檢修記錄")
        response = self.events.post(
            state=self.client.state or state,
            current_focus=record_tab,
            event_type="click",
            target_id=record_tab,
            value="",
            xhr_seq=7,
        )
        records: list[dict[str, str]] = []
        expected_start = 1
        expected_total: int | None = None
        xhr_seq = 8
        while True:
            schema = parse_maximo_table_schema(
                response, required_headers=RECORD_HEADERS
            )
            _, soup = _parse_maximo_markup(response)
            table = soup.find("table", id=f"{schema.prefix}_tbod-tbd")
            summary = str(table.get("summary", "")) if table is not None else ""
            if not summary.startswith("工作單的作業 "):
                raise MMISClientError("檢修記錄找不到工作單的作業表格")
            _, rows = parse_maximo_table(
                response, required_headers=RECORD_HEADERS, table_summary=summary
            )
            page = parse_maximo_page_info(
                response, table_prefix=schema.prefix, context_name="檢修記錄"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("檢修記錄分頁總筆數不一致")
            if page.total == 0:
                if rows or page.start != 0 or page.end != 0 or page.next_page_target:
                    raise MMISClientError("檢修記錄空頁與表格資料不一致")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("檢修記錄分頁範圍與資料不一致")
            records.extend(
                {field: str(row[field]).strip() for field in RECORD_FIELDS}
                for row in rows if str(row["備註"]).strip()
            )
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("檢修記錄末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("檢修記錄尚未讀完但找不到下一頁")
            expected_start = page.end + 1
            response = self.events.post(
                state=self.client.state or state,
                current_focus=page.next_page_target,
                event_type="click",
                target_id=page.next_page_target,
                value="",
                xhr_seq=xhr_seq,
            )
            xhr_seq += 1
        return {
            "query_name": "查詢定期檢修工單明細",
            "query_work_order_number": number,
            "success": True,
            "檢修記錄": {"count": len(records), "records": records},
        }
