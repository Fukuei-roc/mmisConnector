from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..auth import MMISClientError, MMISSession, PageState
from ..daily_inspection.reader import normalize_work_order
from ..events import MaximoEventClient
from ..parser import (
    _parse_maximo_markup,
    MaximoTableSchema,
    parse_maximo_page_info,
    parse_maximo_tab_target,
    parse_maximo_table,
    parse_maximo_table_schema,
)


LIST_HEADERS = {"工作單"}
RECORD_FIELDS = ("裝置名稱", "檢修項目", "回報結果", "備註")
RECORD_HEADERS = set(RECORD_FIELDS)
NOTE_FIELDS = (
    "車組/車號", "故障類別", "故障類別說明", "故障現象", "故障原因",
    "處置措施", "材料編號(PA)", "員工代號", "人員姓名",
)
NOTE_SUMMARY = "紀事(備註)清單"
MAINTENANCE_FIELDS = ("維修情形", "維修情形(詳述)")
BASIC_FIELDS = (
    "工作單", "車組/車號", "檢修級別", "檢修日期", "完工日期", "工作單狀態",
)
DATE_FIELDS = {"檢修日期", "完工日期"}


def _read_basic_info(detail: str, *, expected_work_order: str) -> dict[str, str]:
    _, soup = _parse_maximo_markup(detail)
    result: dict[str, str] = {}
    for field in BASIC_FIELDS:
        values: list[str] = []
        for label in soup.find_all("label", attrs={"for": True}):
            if label.get_text(" ", strip=True).rstrip(":：").strip() != field:
                continue
            control = soup.find("input", id=str(label["for"]))
            if control is None or any(
                re.search(r"(?:^|;)\s*display\s*:\s*none\b", str(node.get("style", "")), re.I)
                for node in (label, control, *label.parents, *control.parents)
            ):
                continue
            value = str(control.get("value", "")).strip()
            if field in DATE_FIELDS and not value:
                value = str(control.get("title", "")).strip()
                if not value and control.get("dojovalue"):
                    try:
                        taipei = timezone(timedelta(hours=8))
                        value = datetime.fromtimestamp(
                            int(str(control["dojovalue"])) / 1000, taipei
                        ).strftime("%Y/%m/%d")
                    except (ValueError, OverflowError, OSError) as exc:
                        raise MMISClientError(f"定期檢修工單基本資料{field}日期無效") from exc
            values.append(value)
        if not values or len(set(values)) != 1:
            raise MMISClientError(f"定期檢修工單基本資料{field}缺失或不一致")
        result[field] = values[0]
    if result["工作單"] != expected_work_order:
        raise MMISClientError("定期檢修工單明細工作單與輸入不相符")
    return result


def _read_maintenance_status(detail: str) -> dict[str, str]:
    _, soup = _parse_maximo_markup(detail)
    dynamic_data = soup.find("td", attrs={"aria-label": "動態資料"})
    if dynamic_data is None:
        raise MMISClientError("定期檢修工單明細缺少動態資料頁簽")
    result: dict[str, str] = {}
    for field in MAINTENANCE_FIELDS:
        controls = []
        for label in dynamic_data.find_all("label", attrs={"for": True}):
            if label.get_text(" ", strip=True).rstrip(":：").strip() != field:
                continue
            control = dynamic_data.find("textarea", id=str(label["for"]))
            if control is not None and not any(
                re.search(r"(?:^|;)\s*display\s*:\s*none\b", str(node.get("style", "")), re.I)
                for node in (control, *control.parents)
                if node is not dynamic_data
            ):
                controls.append(control)
        if len(controls) != 1:
            raise MMISClientError(f"定期檢修工單動態資料找不到唯一的{field}欄位")
        result[field] = controls[0].get_text()
    return result


class PeriodicInspectionWorkOrderDetailReader:
    """Read nonempty inspection remarks from one exact ZZ_PMWO work order."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.events = MaximoEventClient(client)

    def _read_important_notes(
        self, *, state: PageState, response: str, xhr_seq: int
    ) -> tuple[dict[str, Any], int]:
        records: list[dict[str, str]] = []
        expected_start = 1
        expected_total: int | None = None
        while True:
            schema, rows = parse_maximo_table(
                response, required_headers=set(NOTE_FIELDS), table_summary=NOTE_SUMMARY
            )
            if schema is None:
                raise MMISClientError("檢修回報缺少紀事(備註)清單表格")
            page = parse_maximo_page_info(
                response, table_prefix=schema.prefix, context_name="紀事清單"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("紀事清單分頁總筆數不一致")
            if page.total == 0:
                if rows or page.start != 0 or page.end != 0 or page.next_page_target:
                    raise MMISClientError("紀事清單空頁與表格資料不一致")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("紀事清單分頁範圍與資料不一致")
            records.extend(
                {field: str(row[field]).strip() for field in NOTE_FIELDS}
                for row in rows
            )
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("紀事清單末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("紀事清單尚未讀完但找不到下一頁")
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
        return {"count": len(records), "records": records}, xhr_seq

    def _filter_work_order(
        self, *, state: PageState, response: str, number: str, xhr_seq: int
    ) -> tuple[str, int]:
        schema = parse_maximo_table_schema(response, required_headers=LIST_HEADERS)
        work_column = next(
            column for column, label in schema.headers.items() if label == "工作單"
        )
        work_input = f"{schema.prefix}_tfrow_[C:{work_column}]_txt-tb"
        self.events.post(
            state=self.client.state or state,
            current_focus=work_input,
            event_type="setvalue",
            target_id=work_input,
            value=number,
            xhr_seq=xhr_seq,
        )
        filtered = self.events.post(
            state=self.client.state or state,
            current_focus=work_input,
            event_type="filterrows",
            target_id=f"{schema.prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=xhr_seq + 1,
        )
        return filtered, xhr_seq + 2

    @staticmethod
    def _exact_filtered_row(
        response: str, *, number: str
    ) -> tuple[MaximoTableSchema, dict[str, Any]] | None:
        schema = parse_maximo_table_schema(response, required_headers=LIST_HEADERS)
        result_schema, rows = parse_maximo_table(
            response, required_headers=LIST_HEADERS
        )
        page = parse_maximo_page_info(
            response, table_prefix=schema.prefix, context_name="定期檢修工單"
        )
        if page.total == 0:
            if rows or page.start != 0 or page.end != 0 or page.next_page_target:
                raise MMISClientError("定期檢修工單零筆結果與表格資料不一致")
            return None
        if result_schema is None or result_schema.prefix != schema.prefix:
            raise MMISClientError("定期檢修工單查詢結果缺少表格")
        if (
            page.total != 1 or page.start != 1 or page.end != 1
            or page.next_page_target is not None or len(rows) != 1
            or rows[0]["工作單"] != number
        ):
            raise MMISClientError("工作單查詢結果不是唯一且完全相符的一筆")
        return schema, rows[0]

    def run(self, work_order: str) -> dict[str, Any]:
        number = normalize_work_order(work_order)
        state, response = self.events.load_app_with_response(
            app_value="ZZ_PMWO",
            favorite_focus="FavoriteApp_ZZ_PMWO",
            expected_app_id="zz_pmwo",
            display_name="定期檢修工單",
        )
        response, xhr_seq = self._filter_work_order(
            state=state, response=response, number=number, xhr_seq=1
        )
        found = self._exact_filtered_row(response, number=number)
        if found is None:
            menu = self.events.post(
                state=self.client.state or state,
                current_focus="toolbar2_tbs_0_tbcb_0_query-tb",
                event_type="click",
                target_id="toolbar2_tbs_0_tbcb_0_query-img",
                value="",
                xhr_seq=xhr_seq,
            )
            xhr_seq += 1
            if "mainrec_menus" not in menu:
                raise MMISClientError("MMIS 未回傳定期檢修工單查詢選單")
            response = self.events.post(
                state=self.client.state or state,
                current_focus="menu0_useAllRecsQuery_OPTION_a",
                event_type="click",
                target_id="mainrec_menus",
                value="useAllRecsQuery_OPTION",
                xhr_seq=xhr_seq,
            )
            xhr_seq += 1
            response, xhr_seq = self._filter_work_order(
                state=state, response=response, number=number, xhr_seq=xhr_seq
            )
            found = self._exact_filtered_row(response, number=number)
            if found is None:
                raise MMISClientError(f"找不到工作單：{number}")
        result_schema, _ = found
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
            xhr_seq=xhr_seq,
        )
        xhr_seq += 1
        basic_info = _read_basic_info(detail, expected_work_order=number)
        maintenance_status = _read_maintenance_status(detail)
        report_tab = parse_maximo_tab_target(detail, title="檢修回報")
        report = self.events.post(
            state=self.client.state or state,
            current_focus=report_tab,
            event_type="click",
            target_id=report_tab,
            value="",
            xhr_seq=xhr_seq,
        )
        xhr_seq += 1
        important_notes, xhr_seq = self._read_important_notes(
            state=state, response=report, xhr_seq=xhr_seq
        )
        record_tab = parse_maximo_tab_target(report, title="檢修記錄")
        response = self.events.post(
            state=self.client.state or state,
            current_focus=record_tab,
            event_type="click",
            target_id=record_tab,
            value="",
            xhr_seq=xhr_seq,
        )
        xhr_seq += 1
        records: list[dict[str, str]] = []
        expected_start = 1
        expected_total: int | None = None
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
            **basic_info,
            "維修程序概況": important_notes,
            "檢修記錄": {"count": len(records), "records": records},
            **maintenance_status,
        }
