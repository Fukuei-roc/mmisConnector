import pytest
import requests

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession, parse_page_state


PAGE = """
<script>
var PAGESEQNUM = "7";
var UISESSIONID = decodeURIComponent("1200");
var CSRFTOKEN = "csrf-value";
var APPID = "startcntr";
</script>
"""


def test_parse_page_state() -> None:
    state = parse_page_state(PAGE, "https://example.test/maximo/ui/")
    assert state.page_seq == 7
    assert state.ui_session_id == "1200"
    assert state.csrf_token == "csrf-value"
    assert state.app_id == "startcntr"


def test_parse_page_state_reports_missing_names_without_values() -> None:
    with pytest.raises(MMISClientError, match="csrf_token"):
        parse_page_state(PAGE.replace('var CSRFTOKEN = "csrf-value";', ""), "https://example.test")


def test_request_rejects_cross_origin_before_network_access() -> None:
    client = MMISSession(
        MMISConfig("user", "password", "https://example.test"),
        session=requests.Session(),
    )
    with pytest.raises(MMISClientError, match="同源"):
        client.request("GET", "https://attacker.example/collect")
