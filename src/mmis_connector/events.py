from __future__ import annotations

import html
import json
import re
from collections.abc import Sequence
from urllib.parse import urljoin

from .auth import MMISClientError, MMISSession, PageState, parse_page_state


EVENT_REDIRECT_RE = re.compile(
    r"<redirect><!\[CDATA\[(?P<url>[^\]]+)\]\]></redirect>"
)


class MaximoEventClient:
    """Send Maximo UI events over the authenticated HTTP session."""

    def __init__(self, client: MMISSession) -> None:
        self.client = client

    def post(
        self,
        *,
        state: PageState,
        current_focus: str,
        event_type: str,
        target_id: str,
        value: str,
        xhr_seq: int,
    ) -> str:
        return self.post_events(
            state=state,
            current_focus=current_focus,
            events=[(event_type, target_id, value)],
            xhr_seq=xhr_seq,
        )

    def post_events(
        self,
        *,
        state: PageState,
        current_focus: str,
        events: Sequence[tuple[str, str, str]],
        xhr_seq: int,
    ) -> str:
        if not events:
            raise MMISClientError("Maximo event 不得為空")
        event_payload = [
            {
                "type": event_type,
                "targetId": target_id,
                "value": value,
                "requestType": "SYNC",
                "csrftokenholder": state.csrf_token,
            }
            for event_type, target_id, value in events
        ]
        payload = {
            "uisessionid": state.ui_session_id,
            "csrftoken": state.csrf_token,
            "currentfocus": current_focus,
            "scrollleftpos": "0",
            "localStorage": "true",
            "scrolltoppos": "0",
            "requesttype": "SYNC",
            "responsetype": "text/xml",
            "events": json.dumps(
                event_payload, ensure_ascii=False, separators=(",", ":")
            ),
        }
        response = self.client.request(
            "POST",
            self.client.event_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": self.client.config.base_url,
                "Referer": state.page_url,
                "qmtry": "1",
                "pageseqnum": str(state.page_seq),
                "xhrseqnum": str(xhr_seq),
            },
        )
        if "exit.jsp?sharedSession=1" in response.text:
            raise MMISClientError("MMIS session 拒絕 event，請重新執行")
        try:
            self.client.state = parse_page_state(response.text, state.page_url)
        except MMISClientError:
            self.client.state = state
        return response.text

    def load_app(
        self,
        *,
        app_value: str,
        favorite_focus: str,
        expected_app_id: str,
        display_name: str,
    ) -> PageState:
        if self.client.state is None:
            self.client.login()
        assert self.client.state is not None
        if self.client.state.app_id.lower() != "startcntr":
            start_url = (
                f"{self.client.config.base_url}/maximo/ui/login"
                f"?uisessionid={self.client.state.ui_session_id}"
                "&event=loadapp&value=startcntr"
            )
            self.client.refresh_state(start_url)

        state, _ = self.client.refresh_state()
        response_text = self.post(
            state=state,
            current_focus=favorite_focus,
            event_type="changeapp",
            target_id="startcntr",
            value=app_value,
            xhr_seq=1,
        )
        redirect_match = EVENT_REDIRECT_RE.search(html.unescape(response_text))
        if redirect_match is None:
            raise MMISClientError(f"切換{display_name}後找不到 redirect")
        redirect_url = urljoin(state.page_url, redirect_match.group("url"))
        app_state, _ = self.client.refresh_state(redirect_url)
        if app_state.app_id.lower() != expected_app_id.lower():
            raise MMISClientError(f"未成功進入{display_name}")
        return app_state
