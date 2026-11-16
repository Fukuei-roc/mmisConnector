from __future__ import annotations

import re
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from .auth import MMISClientError, MMISSession
from .events import MaximoEventClient


APP_ID = "zz_bchappr"
EXPECTED_CATEGORIES = (
    "1A工單", "定期檢修工單", "臨時檢修工單", "貨車定期檢修工單",
    "貨車臨時檢修工單", "特洗消毒除蟑月結單", "貨車不定期檢修工單",
    "客車不定期檢修工單", "柴油客車1A工單", "段修品工單",
    "設備工具定期工單", "設備工具臨修工單", "集電弓檢查工單",
    "監洗檢查表", "權限問題單申請", "PR請購作業", "PO採購作業",
)
COUNT_TITLE_RE = re.compile(r"^(.+?)\((\d+)\)$")


def parse_pending_counts(page_html: str) -> dict[str, int]:
    soup = BeautifulSoup(page_html, "html.parser")
    if soup.body is None or soup.body.get("data-appid", "").lower() != APP_ID:
        raise MMISClientError("回應不是批次核簽頁面")

    counts: dict[str, int] = {}
    for tab in soup.select('li[ctype="tab"] > a[role="tab"][title]'):
        match = COUNT_TITLE_RE.fullmatch(str(tab["title"]).strip())
        if match is None or match.group(1) not in EXPECTED_CATEGORIES:
            continue
        category = match.group(1)
        if category in counts:
            raise MMISClientError(f"批次核簽頁面重複類型: {category}")
        counts[category] = int(match.group(2))

    missing = set(EXPECTED_CATEGORIES) - counts.keys()
    if missing:
        raise MMISClientError("批次核簽頁面缺少類型: " + "、".join(sorted(missing)))
    return {category: counts[category] for category in EXPECTED_CATEGORIES}


def query_pending_counts(client: MMISSession) -> dict[str, int]:
    _, page_html = MaximoEventClient(client).load_app_with_response(
        app_value="ZZ_BCHAPPR",
        favorite_focus="",
        expected_app_id=APP_ID,
        display_name="批次核簽",
    )
    return parse_pending_counts(page_html)


def _one_id(text: str, suffix: str) -> str:
    ids = set(re.findall(r'id=["\']?([\w\[\]:-]+' + re.escape(suffix) + r')', text))
    if len(ids) != 1:
        raise MMISClientError(f"批次核簽找不到唯一的 {suffix} 控制項")
    return ids.pop()


def _check_event_response(text: str) -> None:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise MMISClientError("批次核簽事件回應不是有效 XML") from exc
    if root.tag != "server_response" or root.find(".//error") is not None:
        raise MMISClientError("批次核簽事件遭 MMIS 拒絕")


def _dialog_default_button(text: str) -> str:
    root = ElementTree.fromstring(text)
    ids = [
        str(button["id"])
        for component in root.findall('.//component[@compid="msgbox-dialog"]')
        for button in BeautifulSoup(component.text or "", "html.parser").select(
            'button[ctype="pushbutton"].default[id]'
        )
    ]
    if len(ids) != 1:
        raise MMISClientError("批次核簽找不到唯一的預設確認按鈕")
    return ids[0]


def _selected_approval_count(text: str) -> int:
    root = ElementTree.fromstring(text)
    messages = [
        BeautifulSoup(component.text or "", "html.parser").get_text(" ", strip=True)
        for component in root.findall('.//component[@compid="msgbox-dialog"]')
        if BeautifulSoup(component.text or "", "html.parser").select_one(
            'button[ctype="pushbutton"].default[id]'
        )
    ]
    numbers = re.findall(r"\d+", messages[0]) if len(messages) == 1 else []
    if len(numbers) != 3:
        raise MMISClientError("無法確認本輪批次核簽筆數")
    selected, approved, rejected = map(int, numbers)
    if not 1 <= selected <= 15 or approved != selected or rejected != 0:
        raise MMISClientError("本輪批次核簽筆數或結果不符預期")
    return approved


def approve_all_pending(client: MMISSession) -> dict[str, int]:
    """Approve one visible page per cycle and count confirmed batches by category."""
    events = MaximoEventClient(client)
    state, page = events.load_app_with_response(
        app_value="ZZ_BCHAPPR",
        favorite_focus="",
        expected_app_id=APP_ID,
        display_name="批次核簽",
    )
    pending = parse_pending_counts(page)
    approved = {category: 0 for category in EXPECTED_CATEGORIES}
    xhr_seq = 1
    while sum(pending.values()):
        soup = BeautifulSoup(page, "html.parser")
        active = [
            tab for tab in soup.select(
                'li[ctype="tab"] > a[role="tab"][aria-expanded="true"][title]'
            )
            if (match := COUNT_TITLE_RE.fullmatch(str(tab["title"]).strip()))
            and match.group(1) in pending
        ]
        if len(active) != 1:
            raise MMISClientError("批次核簽無法確認目前頁簽")
        match = COUNT_TITLE_RE.fullmatch(str(active[0]["title"]).strip())
        if match is None or match.group(1) not in pending or pending[match.group(1)] == 0:
            raise MMISClientError("目前頁簽沒有待簽工單，無法繼續核簽")
        category = match.group(1)
        select_id = _one_id(page, "_ttselallrows-ti")
        approve_id = _one_id(page, "_bg_button_EXEWOAPPR-pb")
        for target in (select_id, approve_id):
            response = events.post(
                state=state, current_focus=target, event_type="click",
                target_id=target, value="false" if target == select_id else "",
                xhr_seq=xhr_seq,
            )
            xhr_seq += 1
            _check_event_response(response)
            if target == select_id and approve_id not in response:
                raise MMISClientError("全選後找不到批次核簽按鈕")
        yes_id = _dialog_default_button(response)
        batch_size = _selected_approval_count(response)
        response = events.post(
            state=state, current_focus=yes_id, event_type="click",
            target_id=yes_id, value="", xhr_seq=xhr_seq,
        )
        xhr_seq += 1
        _check_event_response(response)
        if "BMXZZ7134I" not in response:
            raise MMISClientError("MMIS 未確認本輪批次核簽成功")
        ok_id = _dialog_default_button(response)
        response = events.post(
            state=state, current_focus=ok_id, event_type="click",
            target_id=ok_id, value="", xhr_seq=xhr_seq,
        )
        xhr_seq += 1
        _check_event_response(response)
        state, page = client.refresh_state()
        if state.app_id.lower() != APP_ID:
            raise MMISClientError("核簽後離開批次核簽頁面")
        current = parse_pending_counts(page)
        approved[category] += batch_size
        pending = current
    return approved
