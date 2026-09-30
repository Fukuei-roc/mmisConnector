from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.query import (
    UNCLOSED_DEPOT_NAME,
    UNCLOSED_INCIDENT_LEVELS,
    UNCLOSED_QUERY_MENU_VALUE,
    UNCLOSED_QUERY_NAME,
    UnclosedFaultNoticeQuery,
)
from mmis_connector.parser import (
    parse_fault_notice_page_info,
    parse_fault_notice_table,
    parse_maximo_table_schema,
)


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
MENU_RESPONSE = "<div>mainrec_menus</div>"
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-09-30_query-unclosed-fault-notices"
    r"\dom\2026-09-30T053113-960.html"
)


def _page(
    start: int,
    end: int,
    total: int,
    *,
    prefix: str = "dynamic_table",
    has_next: bool,
    include_query_name: bool = True,
) -> str:
    rows = "".join(
        f'''<tr id="{prefix}_tbod_tdrow-tr[R:{row - start}]">
          <td id="{prefix}_tdrow_[C:1]-c[R:{row - start}]">
            <span id="{prefix}_col_1_ttxt-lb[R:{row - start}]"
                  title="notice-{row}"></span>
          </td>
          <td id="{prefix}_tdrow_[C:5]-c[R:{row - start}]">
            <span id="{prefix}_col_5_ttxt-lb[R:{row - start}]"
                  title="A"></span>
          </td>
          <td id="{prefix}_tdrow_[C:16]-c[R:{row - start}]">
            <span id="{prefix}_col_16_ttxt-lb[R:{row - start}]"
                  title="新竹機務段"></span>
          </td>
        </tr>'''
        for row in range(start, end + 1)
    )
    next_image = "tablebtn_next_on.gif" if has_next else "tablebtn_next_off.gif"
    query_name = UNCLOSED_QUERY_NAME if include_query_name else ""
    return f'''<response><component><![CDATA[
      <span>{query_name}</span>
      <label id="{prefix}-lb3" class="tCount">{start} - {end}/{total}</label>
      <a id="{prefix}-ti7"><img id="{prefix}-ti7_img" src="{next_image}" /></a>
      <div id="{prefix}_ttrow_[C:1]_ttitle-lb">通報號</div>
      <div id="{prefix}_ttrow_[C:5]_ttitle-lb">事故等級</div>
      <div id="{prefix}_ttrow_[C:16]_ttitle-lb">配屬段別名稱</div>
      {rows}
    ]]></component></response>'''


def _empty_page() -> str:
    return (
        f"<span>{UNCLOSED_QUERY_NAME}</span>"
        "<message>沒有要顯示的列。</message>"
    )


def _run_with_responses(
    monkeypatch: pytest.MonkeyPatch,
    *,
    selected_response: str,
    filtered_response: str,
    additional_pages: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    client = SimpleNamespace(state=STATE)
    query = UnclosedFaultNoticeQuery(client)
    post_calls: list[dict[str, Any]] = []
    multi_calls: list[dict[str, Any]] = []
    responses = iter(
        [MENU_RESPONSE, selected_response, "<response>depot set</response>", *(additional_pages or [])]
    )

    monkeypatch.setattr(query, "_load_fault_notice_app", lambda: STATE)

    def fake_post_event(**kwargs: Any) -> str:
        post_calls.append(kwargs)
        return next(responses)

    def fake_post_events(**kwargs: Any) -> str:
        multi_calls.append(kwargs)
        return filtered_response

    monkeypatch.setattr(query, "_post_event", fake_post_event)
    monkeypatch.setattr(query, "_post_events", fake_post_events)
    return query.run(), post_calls, multi_calls


def test_run_uses_dynamic_targets_and_collects_all_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, post_calls, multi_calls = _run_with_responses(
        monkeypatch,
        selected_response=_page(1, 1, 1, prefix="alpha", has_next=False),
        filtered_response=_page(1, 20, 31, prefix="alpha", has_next=True),
        additional_pages=[
            _page(21, 31, 31, prefix="alpha", has_next=False)
        ],
    )

    assert result == {
        "success": True,
        "query_name": UNCLOSED_QUERY_NAME,
        "filters": {
            "配屬段別名稱": UNCLOSED_DEPOT_NAME,
            "事故等級": UNCLOSED_INCIDENT_LEVELS,
        },
        "count": 31,
        "records": result["records"],
    }
    assert len(result["records"]) == 31
    assert post_calls[1]["value"] == UNCLOSED_QUERY_MENU_VALUE
    assert post_calls[2] == {
        "state": STATE,
        "current_focus": "alpha_tfrow_[C:5]_txt-tb",
        "event_type": "setvalue",
        "target_id": "alpha_tfrow_[C:16]_txt-tb",
        "value": UNCLOSED_DEPOT_NAME,
        "xhr_seq": 3,
    }
    assert multi_calls == [
        {
            "state": STATE,
            "current_focus": "alpha_tfrow_[C:5]_txt-tb",
            "events": [
                (
                    "setvalue",
                    "alpha_tfrow_[C:5]_txt-tb",
                    UNCLOSED_INCIDENT_LEVELS,
                ),
                ("filterrows", "alpha_tbod_tfrow-tr", ""),
            ],
            "xhr_seq": 4,
        }
    ]
    assert post_calls[-1]["target_id"] == "alpha-ti7"
    assert post_calls[-1]["xhr_seq"] == 5


def test_run_accepts_empty_filtered_result(monkeypatch: pytest.MonkeyPatch) -> None:
    result, post_calls, _ = _run_with_responses(
        monkeypatch,
        selected_response=_page(1, 1, 1, has_next=False),
        filtered_response=_empty_page(),
    )

    assert result["count"] == 0
    assert result["records"] == []
    assert len(post_calls) == 3


def test_run_rejects_selected_query_without_required_filter_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(MMISClientError, match="符合條件"):
        _run_with_responses(
            monkeypatch,
            selected_response=(
                f"<span>{UNCLOSED_QUERY_NAME}</span>"
                '<div id="table_ttrow_[C:1]_ttitle-lb">通報號</div>'
            ),
            filtered_response=_empty_page(),
        )


def test_run_accepts_filter_fragment_without_repeated_query_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _, _ = _run_with_responses(
        monkeypatch,
        selected_response=_page(1, 1, 1, has_next=False),
        filtered_response=_page(
            1, 1, 1, has_next=False, include_query_name=False
        ),
    )

    assert result["count"] == 1


def test_run_rejects_selected_response_without_query_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(MMISClientError, match="未確認已套用"):
        _run_with_responses(
            monkeypatch,
            selected_response=_page(
                1, 1, 1, has_next=False, include_query_name=False
            ),
            filtered_response=_empty_page(),
        )


@pytest.mark.skipif(not RECORDED_DOM.is_file(), reason="local recording unavailable")
def test_recorded_dom_has_expected_dynamic_schema_and_first_page_shape() -> None:
    response_text = RECORDED_DOM.read_text(encoding="utf-8")
    schema = parse_maximo_table_schema(
        response_text,
        required_headers={"通報號", "事故等級", "配屬段別名稱"},
    )
    page_info = parse_fault_notice_page_info(response_text)
    records = parse_fault_notice_table(response_text)

    assert schema.headers[5] == "事故等級"
    assert schema.headers[16] == "配屬段別名稱"
    assert (page_info.start, page_info.end, page_info.total) == (1, 20, 31)
    assert page_info.next_page_target == f"{schema.prefix}-ti7"
    assert len(records) == 20
