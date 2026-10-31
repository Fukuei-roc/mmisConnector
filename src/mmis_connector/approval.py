from __future__ import annotations

from collections.abc import Callable
from .auth import MMISClientError, PageState
from .parser import (
    FaultNoticePageInfo, parse_maximo_page_info, parse_maximo_tab_target,
    parse_maximo_table,
)


def parse_approval_page(response: str) -> tuple[list[str], FaultNoticePageInfo]:
    schema, rows = parse_maximo_table(
        response, required_headers={"姓名", "核簽結果"}, table_summary="核簽流程"
    )
    if schema is None:
        raise MMISClientError("核簽流程缺少必要欄位")
    page = parse_maximo_page_info(
        response, table_prefix=schema.prefix, context_name="核簽流程"
    )
    if page.total == 0:
        if rows or page.start != 0 or page.end != 0 or page.next_page_target:
            raise MMISClientError("核簽流程空頁與表格資料不一致")
    elif page.end - page.start + 1 != len(rows):
        raise MMISClientError("核簽流程分頁範圍與資料不一致")
    names = []
    for row in rows:
        if row["核簽結果"] == "目前進行者":
            name = str(row["姓名"]).strip()
            if not name:
                raise MMISClientError("核簽流程目前進行者缺少姓名")
            names.append(name)
    return names, page


def read_pending_approvers(
    *, detail: str, get_state: Callable[[], PageState], xhr_seq: int,
    post_event: Callable[..., str],
) -> tuple[list[str], int]:
    approval_tab = parse_maximo_tab_target(detail, title="核簽記錄")
    response = post_event(
        state=get_state(), current_focus=approval_tab, event_type="click",
        target_id=approval_tab, value="", xhr_seq=xhr_seq,
    )
    xhr_seq += 1
    names: list[str] = []
    expected_start = 1
    expected_total: int | None = None
    while True:
        current_names, page = parse_approval_page(response)
        if expected_total is None:
            expected_total = page.total
        if page.total != expected_total:
            raise MMISClientError("核簽流程分頁總筆數不一致")
        if page.total == 0:
            break
        if page.start != expected_start:
            raise MMISClientError("核簽流程分頁起點不連續")
        names.extend(current_names)
        if page.end == page.total:
            if page.next_page_target is not None:
                raise MMISClientError("核簽流程末頁仍有下一頁")
            break
        if page.next_page_target is None:
            raise MMISClientError("核簽流程尚未讀完但找不到下一頁")
        expected_start = page.end + 1
        response = post_event(
            state=get_state(), current_focus=page.next_page_target,
            event_type="click", target_id=page.next_page_target,
            value="", xhr_seq=xhr_seq,
        )
        xhr_seq += 1
    return sorted(set(names)), xhr_seq
