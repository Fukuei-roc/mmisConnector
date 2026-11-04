from __future__ import annotations

from typing import Any

from ..auth import MMISClientError, MMISSession
from ..parser import _parse_maximo_markup
from .reader import DailyInspectionWorkOrderDetailReader, parse_daily_inspection_basic_info


EXPECTED_STATUS = "執行中未派工"
CANCEL_REASON = "重複開單"


def _dialog_controls(response: str, dialog_id: str) -> tuple[str, str]:
    _, soup = _parse_maximo_markup(response)
    dialog = soup.find(id=f"{dialog_id}-dialog_inner")
    if dialog is None:
        raise MMISClientError(f"MMIS 未顯示{dialog_id}確認視窗；取消結果不明，請人工確認")
    if dialog_id == "ZZ_WOCAN":
        fields = dialog.find_all("textarea", id=True)
        if len(fields) != 1:
            raise MMISClientError("找不到唯一的取消理由欄位")
        field_id = str(fields[0]["id"])
    else:
        field_id = ""
    buttons = [button for button in dialog.find_all(id=True)
               if button.get_text(" ", strip=True) in ({"確定"} if dialog_id == "ZZ_WOCAN" else {"是"})]
    if len(buttons) != 1:
        raise MMISClientError("找不到唯一的確認按鈕；取消結果不明，請人工確認")
    return field_id, str(buttons[0]["id"])


class DailyInspectionWorkOrderCanceller:
    def __init__(self, client: MMISSession) -> None:
        self.client = client
        self.reader = DailyInspectionWorkOrderDetailReader(client)
        self.events = self.reader.events

    def run(self, work_order: str) -> dict[str, Any]:
        number, detail = self.reader.open_detail(work_order)
        info = parse_daily_inspection_basic_info(detail, expected_work_order=number)
        if info["工作單狀態"] != EXPECTED_STATUS:
            raise MMISClientError("非執行中未派工工單不可刪除")
        if self.client.state is None:
            raise MMISClientError("MMIS 回應缺少目前頁面狀態")
        _, soup = _parse_maximo_markup(detail)
        action = soup.find(id="toolactions_ZZ_WOCAN-tbb")
        if action is None or action.find(attrs={"title": "工單取消"}) is None:
            raise MMISClientError("找不到工單取消按鈕")

        try:
            dialog = self.events.post(
                state=self.client.state, current_focus="toolactions_ZZ_WOCAN-tbb",
                event_type="click", target_id="toolactions_ZZ_WOCAN-tbb",
                value="", xhr_seq=6,
            )
            reason_id, confirm_id = _dialog_controls(dialog, "ZZ_WOCAN")
            confirmation = self.events.post_events(
                state=self.client.state, current_focus=confirm_id,
                events=[("setvalue", reason_id, CANCEL_REASON), ("click", confirm_id, "")],
                xhr_seq=7,
            )
            _, yes_id = _dialog_controls(confirmation, "msgbox")
            self.events.post(
                state=self.client.state, current_focus=yes_id,
                event_type="click", target_id=yes_id, value="", xhr_seq=8,
            )
        except MMISClientError as exc:
            raise MMISClientError("工單取消結果不明，請人工確認；程式未自動重送") from exc

        try:
            _, verified = self.reader.open_detail(number)
            status = parse_daily_inspection_basic_info(
                verified, expected_work_order=number
            )["工作單狀態"]
        except MMISClientError as exc:
            raise MMISClientError("工單取消後無法確認狀態，請人工確認") from exc
        if status != "工單取消":
            raise MMISClientError(f"工單取消後狀態為「{status}」，請人工確認")
        return {"success": True, "工作單": number, "工作單狀態": status}
