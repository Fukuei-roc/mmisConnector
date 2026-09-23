import json
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.events import MaximoEventClient


STATE = PageState("session", 3, "csrf", "startcntr", "https://example.test/start")


class Response:
    def __init__(self, text: str) -> None:
        self.text = text


def test_post_builds_maximo_event_without_logging_sensitive_state() -> None:
    calls = []

    def request(*args, **kwargs):
        calls.append((args, kwargs))
        return Response("<server_response />")

    client = SimpleNamespace(
        event_url="https://example.test/maximo.jsp",
        config=SimpleNamespace(base_url="https://example.test"),
        request=request,
        state=STATE,
    )

    MaximoEventClient(client).post(
        state=STATE,
        current_focus="focus",
        event_type="setvalue",
        target_id="field",
        value="703",
        xhr_seq=4,
    )

    _, kwargs = calls[0]
    event = json.loads(kwargs["data"]["events"])[0]
    assert event == {
        "type": "setvalue",
        "targetId": "field",
        "value": "703",
        "requestType": "SYNC",
        "csrftokenholder": "csrf",
    }
    assert kwargs["headers"]["xhrseqnum"] == "4"
    assert client.state == STATE


def test_post_rejects_shared_session_response() -> None:
    client = SimpleNamespace(
        event_url="https://example.test/maximo.jsp",
        config=SimpleNamespace(base_url="https://example.test"),
        request=lambda *args, **kwargs: Response("exit.jsp?sharedSession=1"),
        state=STATE,
    )

    with pytest.raises(MMISClientError, match="session 拒絕"):
        MaximoEventClient(client).post(
            state=STATE,
            current_focus="focus",
            event_type="click",
            target_id="target",
            value="",
            xhr_seq=1,
        )
