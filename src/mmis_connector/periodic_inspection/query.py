from __future__ import annotations

from datetime import datetime
import re

from ..auth import MMISClientError, MMISSession
from ..daily_inspection.query import normalize_vehicle
from ..events import MaximoEventClient
from ..parser import parse_maximo_page_info, parse_maximo_table, parse_maximo_table_schema


FIELDS = ("車組/車號", "檢修級別", "工作單", "檢修日期")
REQUIRED_HEADERS = {*FIELDS, "檢修單位", "工作單狀態"}
INSPECTION_UNIT = "檢查室"
WORK_ORDER_STATUS = "工單結案,簽核中"


class LatestPeriodicInspectionWorkOrderQuery:
    """Find the newest matching ZZ_PMWO work order across every result page."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.events = MaximoEventClient(client)

    def run(self, vehicle: str) -> dict[str, str]:
        normalized_vehicle = normalize_vehicle(vehicle)
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
        for xhr_seq, (field, value) in enumerate(
            (
                ("車組/車號", normalized_vehicle),
                ("檢修單位", INSPECTION_UNIT),
                ("工作單狀態", WORK_ORDER_STATUS),
            ),
            start=3,
        ):
            target = f"{schema.prefix}_tfrow_[C:{columns[field]}]_txt-tb"
            self.events.post(
                state=self.client.state or state,
                current_focus=target,
                event_type="setvalue",
                target_id=target,
                value=value,
                xhr_seq=xhr_seq,
            )
        filter_target = f"{schema.prefix}_tbod_tfrow-tr"
        response = self.events.post(
            state=self.client.state or state,
            current_focus=filter_target,
            event_type="filterrows",
            target_id=filter_target,
            value="",
            xhr_seq=6,
        )

        latest: dict[str, str] | None = None
        latest_key: tuple[datetime, str] | None = None
        expected_start = 1
        expected_total: int | None = None
        xhr_seq = 7
        while True:
            page_schema = parse_maximo_table_schema(response, required_headers=REQUIRED_HEADERS)
            if page_schema.prefix != schema.prefix:
                raise MMISClientError("定期檢修工單分頁表格已變更")
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
                raise MMISClientError(f"找不到車組/車號 {normalized_vehicle} 的定期檢修工單")
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("定期檢修工單分頁範圍與資料不一致")
            for row in rows:
                selected = {field: str(row[field]).strip() for field in FIELDS}
                if not all(selected.values()):
                    raise MMISClientError("定期檢修工單結果缺少必要欄位")
                if normalized_vehicle not in selected["車組/車號"]:
                    raise MMISClientError("定期檢修工單結果車組/車號與查詢條件不符")
                if (
                    str(row["檢修單位"]).strip() != INSPECTION_UNIT
                    or str(row["工作單狀態"]).strip() not in WORK_ORDER_STATUS.split(",")
                ):
                    raise MMISClientError("定期檢修工單結果與篩選條件不符")
                if re.fullmatch(r"\d{4}/\d{2}/\d{2}", selected["檢修日期"]) is None:
                    raise MMISClientError("定期檢修工單結果檢修日期格式無效")
                try:
                    date = datetime.strptime(selected["檢修日期"], "%Y/%m/%d")
                except ValueError as exc:
                    raise MMISClientError("定期檢修工單結果檢修日期無效") from exc
                if date.strftime("%Y/%m/%d") != selected["檢修日期"]:
                    raise MMISClientError("定期檢修工單結果檢修日期格式無效")
                key = (date, selected["工作單"])
                if latest_key is None or key > latest_key:
                    latest_key, latest = key, selected
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
                xhr_seq=xhr_seq,
            )
            xhr_seq += 1
        if latest is None:
            raise MMISClientError("定期檢修工單結果缺少資料")
        return latest
