from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..auth import MMISClientError, MMISSession
from ..daily_inspection.reader import (
    FAULT_HEADERS,
    FAULT_TABLE_SUMMARY,
    normalize_work_order,
)
from ..events import MaximoEventClient
from ..parser import (
    _parse_maximo_markup,
    parse_maximo_page_info,
    parse_maximo_tab_target,
    parse_maximo_table,
    parse_maximo_table_schema,
)


QUERY_NAME = "查詢臨時檢修工單的維修程序概況"
LIST_HEADERS = {"工作單", "檢修級別", "車組/車號"}
NOTE_FIELDS = (
    "故障類別", "故障現象", "故障原因", "處置措施", "維修程序",
    "材料編號(PA)", "更換數量",
)
DESCRIPTION_HEADERS = ("故障類別說明", "故障類型說明")
SUPPLEMENT_FIELDS = {
    "故障現象": (
        {"其它問題", "其他問題"},
        {"其它故障現象", "其他故障現象"},
    ),
    "故障原因": (
        {"其它原因", "其他原因"},
        {"其它故障原因", "其他故障原因"},
    ),
    "處置措施": (
        {"其它", "其他"},
        {"其它處置措施", "其他處置措施"},
    ),
}
BASIC_FIELDS = (
    "車組/車號", "檢修級別", "故障現象", "原因說明", "備註",
    "檢修日期", "完工日期", "工作單狀態",
)
DATE_FIELDS = {"檢修日期", "完工日期"}


def _note_table_summary(response: str) -> str:
    """Distinguish the replacement quantity table from the legacy quantity table."""
    _, soup = _parse_maximo_markup(response)
    matches: list[str] = []
    for table in soup.find_all("table", summary=True):
        summary = str(table["summary"])
        if not summary.startswith("紀事(備註)清單("):
            continue
        headers = {
            node.get_text(" ", strip=True).split("[", 1)[0].strip()
            for node in table.find_all(id=True)
            if str(node["id"]).endswith("_ttitle-lb")
        }
        if set(NOTE_FIELDS).issubset(headers) and any(
            description in headers for description in DESCRIPTION_HEADERS
        ):
            matches.append(summary)
    if len(matches) != 1:
        raise MMISClientError("檢修回報找不到唯一的更換數量紀事清單")
    return matches[0]


def _note_record(
    row: dict[str, Any], *, vehicle: str, description_header: str
) -> dict[str, str]:
    record = {
        "車組/車號": str(row.get("車組/車號") or vehicle),
        "故障類別": str(row["故障類別"]),
        "故障類別說明": str(row[description_header]),
    }
    record.update({field: str(row[field]) for field in NOTE_FIELDS[1:]})
    return record


def _basic_field_value(control: Any, *, field: str) -> str:
    if control.name == "textarea":
        return control.get_text()
    value = str(control.get("value", ""))
    if field not in DATE_FIELDS or value:
        return value
    title = str(control.get("title", ""))
    if title:
        return title
    timestamp = control.get("dojovalue")
    if not timestamp:
        return ""
    try:
        taipei = timezone(timedelta(hours=8))
        return datetime.fromtimestamp(int(str(timestamp)) / 1000, taipei).strftime(
            "%Y/%m/%d"
        )
    except (ValueError, OverflowError, OSError) as exc:
        raise MMISClientError(f"臨時檢修工單{field}日期無效") from exc


def parse_temporary_repair_basic_info(response: str) -> dict[str, str]:
    """Read visible work-order fields by label/for, including duplicate date controls."""
    _, soup = _parse_maximo_markup(response)
    result: dict[str, str] = {}
    for field in BASIC_FIELDS:
        values = []
        for label in soup.find_all("label", attrs={"for": True}):
            if label.get_text(" ", strip=True).rstrip(":：").strip() != field:
                continue
            control = soup.find(id=str(label["for"]))
            if control is None or control.name not in {"input", "textarea"}:
                raise MMISClientError(f"臨時檢修工單基本資料找不到{field}輸入欄位")
            values.append(_basic_field_value(control, field=field))
        if not values or len(set(values)) != 1:
            raise MMISClientError(f"臨時檢修工單基本資料{field}缺失或不一致")
        result[field] = values[0]
    return result


def parse_temporary_repair_linked_fault_notices(
    response: str,
) -> dict[str, Any]:
    """Read the same linked-notice table contract used by daily inspection."""
    schema, records = parse_maximo_table(
        response,
        required_headers=FAULT_HEADERS,
        table_summary=FAULT_TABLE_SUMMARY,
        normalize_line_breaks=True,
    )
    if schema is None:
        raise MMISClientError("臨時檢修工單找不到故障通報管理表格")
    page = parse_maximo_page_info(
        response, table_prefix=schema.prefix, context_name=FAULT_TABLE_SUMMARY
    )
    if (
        page.total != len(records)
        or page.next_page_target is not None
        or (records and (page.start != 1 or page.end != len(records)))
    ):
        raise MMISClientError("故障通報管理結果超過單頁或分頁不一致，拒絕回傳不完整資料")
    return {"count": len(records), "records": records}


def _selected_note_row(response: str, *, table_prefix: str) -> int | None:
    """Find the row whose detail pane is currently rendered."""
    _, soup = _parse_maximo_markup(response)
    table = soup.find("table", id=f"{table_prefix}_tbod-tbd")
    if table is None:
        raise MMISClientError("紀事清單找不到資料表格")
    pattern = re.compile(rf"^{re.escape(table_prefix)}_tbod_tdrow-tr\[R:(\d+)\]$")
    selected = []
    for row in table.find_all("tr", id=True):
        match = pattern.fullmatch(str(row["id"]))
        if match and row.get("currentrow") == "true":
            selected.append(int(match.group(1)))
    if len(selected) > 1:
        raise MMISClientError("紀事清單有多筆目前選取列")
    return selected[0] if selected else None


def _supplemental_note_fields(
    response: str,
    *,
    table_prefix: str,
    rendered: dict[str, tuple[str, str]] | None = None,
) -> dict[str, tuple[str, str]]:
    """Apply Maximo's partial textarea updates to the rendered detail values."""
    _, soup = _parse_maximo_markup(response)
    scope = soup.find("table", id=f"{table_prefix}_tdet-chld") or soup
    values = dict(rendered or {})
    for field, (_, labels) in SUPPLEMENT_FIELDS.items():
        controls = []
        for label in scope.find_all("label", attrs={"for": True}):
            name = label.get_text(" ", strip=True).rstrip(":：").strip()
            if name not in labels:
                continue
            textarea = scope.find("textarea", id=str(label["for"]))
            if textarea is None:
                raise MMISClientError(f"紀事明細的{field}補充欄位缺少 textarea")
            controls.append(textarea)
        if len(controls) > 1:
            raise MMISClientError(f"紀事明細有多個{field}補充欄位")
        if controls:
            control = controls[0]
            values[field] = str(control["id"]), control.get_text().strip()
        elif field in values:
            control_id, _ = values[field]
            control = scope.find("textarea", id=control_id)
            if control is not None:
                values[field] = control_id, control.get_text().strip()
    return values


def _confirm_selected_note_row(response: str, *, table_prefix: str, row: int) -> None:
    """Do not reuse a prior detail value unless the row selection was acknowledged."""
    _, soup = _parse_maximo_markup(response)
    selected = soup.find("tr", id=f"{table_prefix}_tbod_tdrow-tr[R:{row}]")
    if selected is not None and selected.get("currentrow") == "true":
        return
    holder = soup.find(
        "component", id=f"{table_prefix}_tbod_tdrow-tr[R:{row}]_holder"
    )
    if holder is not None and re.search(
        r"setAttribute\(\s*['\"]currentrow['\"]\s*,\s*['\"]true['\"]\s*\)",
        str(holder),
    ):
        return
    raise MMISClientError("紀事清單未確認切換至指定資料列")


class TemporaryRepairProcedureReader:
    """Read all maintenance note rows for one exact temporary repair work order."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.events = MaximoEventClient(client)

    def run(self, work_order: str) -> dict[str, Any]:
        number = normalize_work_order(work_order)
        state = self.events.load_app(
            app_value="ZZ_CMWO",
            favorite_focus="FavoriteApp_ZZ_CMWO",
            expected_app_id="zz_cmwo",
            display_name="臨時檢修工單",
        )
        menu = self.events.post(
            state=state,
            current_focus="toolbar2_tbs_0_tbcb_0_query-tb",
            event_type="click",
            target_id="toolbar2_tbs_0_tbcb_0_query-img",
            value="",
            xhr_seq=1,
        )
        if "mainrec_menus" not in menu:
            raise MMISClientError("MMIS 未回傳臨時檢修工單查詢選單")
        response = self.events.post(
            state=self.client.state or state,
            current_focus="menu0_useAllRecsQuery_OPTION_a",
            event_type="click",
            target_id="mainrec_menus",
            value="useAllRecsQuery_OPTION",
            xhr_seq=2,
        )
        schema = parse_maximo_table_schema(response, required_headers=LIST_HEADERS)
        prefix = schema.prefix
        columns = {label: index for index, label in schema.headers.items()}
        work_input = f"{prefix}_tfrow_[C:{columns['工作單']}]_txt-tb"
        level_input = f"{prefix}_tfrow_[C:{columns['檢修級別']}]_txt-tb"
        self.events.post(
            state=self.client.state or state,
            current_focus=level_input,
            event_type="setvalue",
            target_id=work_input,
            value=number,
            xhr_seq=3,
        )
        self.events.post(
            state=self.client.state or state,
            current_focus=work_input,
            event_type="setvalue",
            target_id=level_input,
            value="C1,C2,C3",
            xhr_seq=4,
        )
        response = self.events.post(
            state=self.client.state or state,
            current_focus=work_input,
            event_type="filterrows",
            target_id=f"{prefix}_tbod_tfrow-tr",
            value="",
            xhr_seq=5,
        )
        result_schema, rows = parse_maximo_table(response, required_headers=LIST_HEADERS)
        if not rows:
            raise MMISClientError(f"找不到工作單：{number}")
        if result_schema is None or len(rows) != 1 or rows[0]["工作單"] != number:
            raise MMISClientError("工作單查詢結果不是唯一且完全相符的一筆")
        page = parse_maximo_page_info(
            response, table_prefix=result_schema.prefix, context_name="臨時檢修工單"
        )
        if page.total != 1 or page.next_page_target is not None:
            raise MMISClientError("工作單查詢結果不是唯一一筆")
        target = f"{result_schema.prefix}_tdrow_[C:{columns['工作單']}]_ttxt-lb[R:0]"
        detail = self.events.post(
            state=self.client.state or state,
            current_focus=target,
            event_type="click",
            target_id=target,
            value="",
            xhr_seq=6,
        )
        basic_info = parse_temporary_repair_basic_info(detail)
        linked_fault_notices = parse_temporary_repair_linked_fault_notices(detail)
        vehicle = basic_info["車組/車號"]
        if vehicle != rows[0]["車組/車號"]:
            raise MMISClientError("工單明細車組/車號與查詢結果不相符")
        tab = parse_maximo_tab_target(detail, title="檢修回報")
        response = self.events.post(
            state=self.client.state or state,
            current_focus=tab,
            event_type="click",
            target_id=tab,
            value="",
            xhr_seq=7,
        )
        summary = _note_table_summary(response)
        records: list[dict[str, str]] = []
        expected_start = 1
        expected_total: int | None = None
        xhr_seq = 8
        while True:
            note_schema, note_rows = parse_maximo_table(
                response, required_headers=set(NOTE_FIELDS), table_summary=summary
            )
            if note_schema is None:
                raise MMISClientError("檢修回報缺少紀事清單表格")
            descriptions = [
                field for field in DESCRIPTION_HEADERS
                if field in note_schema.headers.values()
            ]
            if len(descriptions) != 1:
                raise MMISClientError("紀事清單故障類別說明表頭不唯一")
            page = parse_maximo_page_info(
                response, table_prefix=note_schema.prefix, context_name="紀事清單"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("紀事清單分頁總筆數不一致")
            if page.total == 0:
                if note_rows:
                    raise MMISClientError("紀事清單空頁含有資料")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(note_rows):
                raise MMISClientError("紀事清單分頁範圍與資料不一致")
            selected_row = _selected_note_row(response, table_prefix=note_schema.prefix)
            rendered_supplements = _supplemental_note_fields(
                response, table_prefix=note_schema.prefix
            )
            for row_number, row in enumerate(note_rows):
                record = _note_record(
                    row, vehicle=vehicle, description_header=descriptions[0]
                )
                supplemental_fields = [
                    field for field, (choices, _) in SUPPLEMENT_FIELDS.items()
                    if record[field] in choices
                ]
                if supplemental_fields:
                    if selected_row != row_number:
                        target = (
                            f"{note_schema.prefix}_tdrow_[C:0]_tgdet-ti"
                            f"[R:{row_number}]"
                        )
                        detail_response = self.events.post(
                            state=self.client.state or state,
                            current_focus=target,
                            event_type="click",
                            target_id=target,
                            value="",
                            xhr_seq=xhr_seq,
                        )
                        xhr_seq += 1
                        _confirm_selected_note_row(
                            detail_response,
                            table_prefix=note_schema.prefix,
                            row=row_number,
                        )
                        selected_row = row_number
                        rendered_supplements = _supplemental_note_fields(
                            detail_response,
                            table_prefix=note_schema.prefix,
                            rendered=rendered_supplements,
                        )
                    for field in supplemental_fields:
                        if field not in rendered_supplements:
                            raise MMISClientError(f"紀事明細找不到{field}補充欄位")
                        supplement = rendered_supplements[field][1]
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
            "success": True,
            "query_name": QUERY_NAME,
            "work_order": number,
            **basic_info,
            "已勾稽故障通報": linked_fault_notices,
            "維修程序概況": {
                "count": len(records),
                "records": records,
            },
        }
