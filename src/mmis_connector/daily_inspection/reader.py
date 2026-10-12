from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..auth import MMISClientError, MMISSession, PageState
from ..parser import (
    SUPPLEMENT_FIELDS,
    _parse_maximo_markup,
    confirm_selected_note_row,
    parse_maximo_page_info,
    parse_maximo_tab_target,
    parse_maximo_table,
    parse_maximo_table_schema,
    selected_note_row,
    supplemental_note_fields,
)
from .query import (
    REQUIRED_HEADERS,
    DailyInspectionWorkOrderQuery,
)


QUERY_NAME = "以工作單號查詢日檢工單內容"
FAULT_TABLE_SUMMARY = "故障通報管理"
FAULT_HEADERS = {"故障通報號", "發生日期", "車組/車號", "故障現象"}
INSPECTION_RECORD_HEADERS = {"裝置名稱", "回報結果", "備註"}
IMPORTANT_NOTE_FIELDS = (
    "車組/車號", "故障類別", "故障類別說明", "故障現象", "故障原因",
    "處置措施", "材料編號(PA)", "員工代號", "人員姓名",
)
IMPORTANT_NOTE_SUMMARY = "紀事(備註)清單"
MAINTENANCE_PERSONNEL_SUMMARY = "檢修人員"
MAINTENANCE_PERSONNEL_FIELDS = ("人員群組", "工作角色", "員工代號", "姓名", "單位")
WORK_ORDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
BASIC_INSPECTION_FIELDS = (
    "工作單", "車組/車號", "檢修日期", "車次", "工作單狀態", "開單人姓名", "開單日期",
)
BASIC_INSPECTION_DATE_FIELDS = {"檢修日期", "開單日期"}


def normalize_work_order(value: str) -> str:
    work_order = value.strip()
    if not work_order or WORK_ORDER_RE.fullmatch(work_order) is None:
        raise MMISClientError("工作單號只能包含英數字與連字號")
    return work_order


def parse_daily_inspection_basic_info(
    response: str, *, expected_work_order: str
) -> dict[str, str]:
    """Read the seven visible fields from the opened 1A work order."""
    _, soup = _parse_maximo_markup(response)
    result: dict[str, str] = {}
    for field in BASIC_INSPECTION_FIELDS:
        values: list[str] = []
        for label in soup.find_all("label", attrs={"for": True}):
            if label.get_text(" ", strip=True).rstrip(":：").strip() != field:
                continue
            control = soup.find("input", id=str(label["for"]))
            if control is None:
                raise MMISClientError(f"日檢工單基本資料找不到「{field}」輸入框")
            value = str(control.get("value", "")).strip()
            if field in BASIC_INSPECTION_DATE_FIELDS and not value:
                value = str(control.get("title", "")).strip()
                if not value and control.get("dojovalue"):
                    try:
                        taipei = timezone(timedelta(hours=8))
                        date = datetime.fromtimestamp(
                            int(str(control["dojovalue"])) / 1000, taipei
                        )
                        value = date.strftime(
                            "%Y/%m/%d %H:%M" if field == "開單日期" else "%Y/%m/%d"
                        )
                    except (ValueError, OverflowError, OSError) as exc:
                        raise MMISClientError(f"日檢工單基本資料「{field}」日期無效") from exc
            values.append(value)
        if not values or len(set(values)) != 1:
            raise MMISClientError(f"日檢工單基本資料「{field}」缺失或不一致")
        result[field] = values[0]
    if result["工作單"] != expected_work_order:
        raise MMISClientError("日檢工單基本資料工作單與輸入不相符")
    return result


def parse_daily_inspection_linked_fault_notices(response: str) -> dict[str, Any]:
    """Read the linked fault notices already rendered in the work order detail."""
    schema, records = parse_maximo_table(
        response,
        required_headers=FAULT_HEADERS,
        table_summary=FAULT_TABLE_SUMMARY,
        normalize_line_breaks=True,
    )
    if schema is None:
        raise MMISClientError("查詢回應找不到故障通報管理表格")
    if records:
        page = parse_maximo_page_info(
            response, table_prefix=schema.prefix, context_name=FAULT_TABLE_SUMMARY
        )
        if (
            page.total != len(records)
            or page.next_page_target is not None
            or page.start != 1
            or page.end != len(records)
        ):
            raise MMISClientError("故障通報管理結果超過單頁，拒絕回傳不完整資料")
    return {"count": len(records), "records": records}


class DailyInspectionWorkOrderDetailReader:
    """Read one 動力車日檢(1A) work order detail without a browser."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.list_query = DailyInspectionWorkOrderQuery(client)
        self.events = self.list_query.events

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

    def open_detail(self, work_order: str) -> tuple[str, str]:
        """Open one exact work order and return its normalized key and detail."""
        normalized_work_order = normalize_work_order(work_order)
        state, list_schema = self.list_query.open_all_records()
        prefix = list_schema.prefix

        self._post_event(
            state=self.client.state or state,
            current_focus=f"{prefix}_tfrow_[C:5]_txt-tb",
            event_type="setvalue",
            target_id=f"{prefix}_tfrow_[C:5]_txt-tb",
            value=normalized_work_order,
            xhr_seq=3,
        )
        result_response = self._post_event(
            state=self.client.state or state,
            current_focus=f"{prefix}_tfrow_[C:5]_txt-tb",
            event_type="filterrows",
            target_id=f"{prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=4,
        )
        result_schema, work_orders = parse_maximo_table(
            result_response,
            required_headers=REQUIRED_HEADERS,
            checkbox_headers={"逾期標註?"},
        )
        if not work_orders:
            raise MMISClientError(f"找不到工作單：{normalized_work_order}")
        if result_schema is None or len(work_orders) != 1:
            raise MMISClientError("工作單查詢結果不是唯一一筆")
        if work_orders[0].get("工作單") != normalized_work_order:
            raise MMISClientError("工作單查詢結果與輸入不相符")

        page_info = parse_maximo_page_info(
            result_response,
            table_prefix=result_schema.prefix,
            context_name="日檢工單",
        )
        if page_info.total != 1 or page_info.next_page_target is not None:
            raise MMISClientError("工作單查詢結果不是唯一一筆")

        work_order_column = next(
            column
            for column, label in result_schema.headers.items()
            if label == "工作單"
        )
        detail_target = (
            f"{result_schema.prefix}_tdrow_[C:{work_order_column}]"
            "_ttxt-lb[R:0]"
        )
        detail_response = self._post_event(
            state=self.client.state or state,
            current_focus=detail_target,
            event_type="click",
            target_id=detail_target,
            value="",
            xhr_seq=5,
        )
        return normalized_work_order, detail_response

    def run(self, work_order: str) -> dict[str, Any]:
        normalized_work_order, detail_response = self.open_detail(work_order)
        linked = parse_daily_inspection_linked_fault_notices(detail_response)

        return {
            "success": True,
            "query_name": QUERY_NAME,
            "work_order": normalized_work_order,
            "has_fault_notices": bool(linked["count"]),
            "count": linked["count"],
            "records": linked["records"],
        }


class DailyInspectionInspectionRecordReader(DailyInspectionWorkOrderDetailReader):
    """Read inspection-record rows with nonempty remarks from one 1A work order."""

    def _read_maintenance_personnel(
        self, response: str, *, state: PageState, xhr_seq: int
    ) -> tuple[dict[str, Any], int]:
        records: list[dict[str, str]] = []
        expected_start = 1
        expected_total: int | None = None
        while True:
            schema, rows = parse_maximo_table(
                response,
                required_headers=set(MAINTENANCE_PERSONNEL_FIELDS),
                table_summary=MAINTENANCE_PERSONNEL_SUMMARY,
            )
            if schema is None:
                raise MMISClientError("檢修人員缺少表格")
            page = parse_maximo_page_info(
                response, table_prefix=schema.prefix, context_name=MAINTENANCE_PERSONNEL_SUMMARY
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("檢修人員分頁總筆數不一致")
            if page.total == 0:
                if rows or page.start != 0 or page.end != 0 or page.next_page_target:
                    raise MMISClientError("檢修人員空頁與表格資料不一致")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("檢修人員分頁範圍與資料不一致")
            records.extend(
                {field: str(row[field]).strip() for field in MAINTENANCE_PERSONNEL_FIELDS}
                for row in rows
            )
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("檢修人員末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("檢修人員尚未讀完但找不到下一頁")
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
        return {"count": len(records), "records": records}, xhr_seq

    def _read_important_notes(
        self, response: str, *, state: PageState, xhr_seq: int
    ) -> tuple[list[dict[str, str]], int]:
        records: list[dict[str, str]] = []
        expected_start = 1
        expected_total: int | None = None
        while True:
            schema, rows = parse_maximo_table(
                response,
                required_headers=set(IMPORTANT_NOTE_FIELDS),
                table_summary=IMPORTANT_NOTE_SUMMARY,
            )
            if schema is None:
                raise MMISClientError("檢修回報缺少紀事清單表格")
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
            selected_row = selected_note_row(response, table_prefix=schema.prefix)
            rendered = supplemental_note_fields(response, table_prefix=schema.prefix)
            for row_number, row in enumerate(rows):
                record = {field: str(row[field]) for field in IMPORTANT_NOTE_FIELDS}
                supplemental_fields = [
                    field for field, (choices, _) in SUPPLEMENT_FIELDS.items()
                    if record[field] in choices
                ]
                if supplemental_fields:
                    if selected_row != row_number:
                        target = f"{schema.prefix}_tdrow_[C:0]_tgdet-ti[R:{row_number}]"
                        detail_response = self._post_event(
                            state=self.client.state or state,
                            current_focus=target,
                            event_type="click",
                            target_id=target,
                            value="",
                            xhr_seq=xhr_seq,
                        )
                        xhr_seq += 1
                        confirm_selected_note_row(
                            detail_response, table_prefix=schema.prefix, row=row_number
                        )
                        selected_row = row_number
                        rendered = supplemental_note_fields(
                            detail_response, table_prefix=schema.prefix,
                            rendered=rendered,
                        )
                    for field in supplemental_fields:
                        if field not in rendered:
                            raise MMISClientError(f"紀事明細找不到{field}補充欄位")
                        supplement = rendered[field][1]
                        if supplement:
                            record[field] += f"：{supplement}"
                records.append(record)
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("紀事清單末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("紀事清單尚未讀完但找不到下一頁")
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
        return records, xhr_seq

    def run(self, work_order: str) -> dict[str, Any]:
        normalized_work_order, detail_response = self.open_detail(work_order)
        basic_info = parse_daily_inspection_basic_info(
            detail_response, expected_work_order=normalized_work_order
        )
        linked_fault_notices = parse_daily_inspection_linked_fault_notices(detail_response)
        state = self.client.state
        if state is None:
            raise MMISClientError("日檢工單明細缺少頁面狀態")
        personnel_tab = parse_maximo_tab_target(
            detail_response, title="檢修人員(單位)"
        )
        personnel_response = self._post_event(
            state=self.client.state or state,
            current_focus=personnel_tab,
            event_type="click",
            target_id=personnel_tab,
            value="",
            xhr_seq=6,
        )
        maintenance_personnel, xhr_seq = self._read_maintenance_personnel(
            personnel_response, state=state, xhr_seq=7
        )
        report_tab = parse_maximo_tab_target(detail_response, title="檢修回報")
        report_response = self._post_event(
            state=self.client.state or state,
            current_focus=report_tab,
            event_type="click",
            target_id=report_tab,
            value="",
            xhr_seq=xhr_seq,
        )
        important_notes, xhr_seq = self._read_important_notes(
            report_response, state=state, xhr_seq=xhr_seq + 1
        )
        record_tab = parse_maximo_tab_target(report_response, title="檢修記錄")
        response = self._post_event(
            state=self.client.state or state,
            current_focus=record_tab,
            event_type="click",
            target_id=record_tab,
            value="",
            xhr_seq=xhr_seq,
        )

        records: list[dict[str, str]] = []
        expected_start = 1
        expected_total: int | None = None
        xhr_seq += 1
        while True:
            schema = parse_maximo_table_schema(
                response, required_headers=INSPECTION_RECORD_HEADERS
            )
            _, soup = _parse_maximo_markup(response)
            table = soup.find("table", id=f"{schema.prefix}_tbod-tbd")
            summary = str(table.get("summary", "")) if table is not None else ""
            if not summary.startswith("工作單的作業 "):
                raise MMISClientError("檢修記錄找不到工作單的作業表格")
            _, rows = parse_maximo_table(
                response,
                required_headers=INSPECTION_RECORD_HEADERS,
                table_summary=summary,
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
                {
                    field: str(row[field]).strip()
                    for field in ("裝置名稱", "回報結果", "備註")
                }
                for row in rows
                if str(row["備註"]).strip()
            )
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("檢修記錄末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("檢修記錄尚未讀完但找不到下一頁")
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

        return {
            **basic_info,
            "success": True,
            "query_name": "查詢日檢工單檢修記錄",
            "work_order": normalized_work_order,
            "count": len(records),
            "records": records,
            "linked_fault_notices": linked_fault_notices,
            "important_notes": {
                "count": len(important_notes), "records": important_notes,
            },
            "maintenance_personnel": maintenance_personnel,
        }
