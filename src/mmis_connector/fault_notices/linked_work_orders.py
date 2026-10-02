from __future__ import annotations

from typing import Any

from ..auth import MMISClientError
from ..parser import parse_maximo_page_info, parse_maximo_tab_target, parse_maximo_table
from .reader import FaultNoticeAnalysisReader, normalize_fault_notice


TABLE_NAME = "檢視所有段檢修工單"
FIELDS = (
    "工作單", "工單級別", "車組/車號", "工作單說明", "工作單狀態", "通報號", "狀態"
)


class LinkedWorkOrdersReader(FaultNoticeAnalysisReader):
    """Read all linked work orders for one exact fault notice over HTTP."""

    def run(self, fault_notice: str) -> dict[str, Any]:
        notice = normalize_fault_notice(fault_notice)
        state, detail_response = self._load_exact_detail(notice)
        tab = parse_maximo_tab_target(detail_response, title="故障追蹤")
        response = self._post_event(
            state=self.client.state or state,
            current_focus=tab,
            event_type="click",
            target_id=tab,
            value="",
            xhr_seq=3,
        )

        records: list[dict[str, str]] = []
        seen: set[str] = set()
        expected_start = 1
        expected_total: int | None = None
        xhr_seq = 4
        while True:
            schema, rows = parse_maximo_table(
                response,
                required_headers=set(FIELDS),
                table_summary=TABLE_NAME,
            )
            if schema is None:
                raise MMISClientError("關聯工單回應缺少表格結構")
            page = parse_maximo_page_info(
                response, table_prefix=schema.prefix, context_name="關聯工單"
            )
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise MMISClientError("關聯工單分頁總筆數不一致")
            if page.total == 0:
                if rows:
                    raise MMISClientError("關聯工單空頁含有資料")
                break
            if page.start != expected_start or page.end - page.start + 1 != len(rows):
                raise MMISClientError("關聯工單分頁範圍與資料不一致")
            for row in rows:
                record = {field: str(row[field]) for field in FIELDS}
                number = record["工作單"].strip()
                if not number:
                    raise MMISClientError("關聯工單資料缺少工作單")
                if number not in seen:
                    records.append(record)
                    seen.add(number)
            if page.end == page.total:
                if page.next_page_target is not None:
                    raise MMISClientError("關聯工單末頁仍有下一頁")
                break
            if page.next_page_target is None:
                raise MMISClientError("關聯工單尚未讀完但找不到下一頁")
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
            "success": True,
            "query_name": "查詢故障通報關聯的工單",
            "fault_notice": notice,
            "count": len(records),
            "records": records,
        }
