from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.query_unprocessed_fault_notices import (
    QUERY_MENU_VALUE,
    QUERY_NAME,
    SECONDARY_QUERY_MENU_VALUE,
    SECONDARY_QUERY_NAME,
    UnprocessedFaultNoticeQuery,
)


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
MENU_RESPONSE = "<div>mainrec_menus</div>"


def _page(
    start: int,
    end: int,
    total: int,
    *,
    query_name: str,
    has_next: bool,
) -> str:
    rows = "".join(
        f'''<tr id="table_tbod_tdrow-tr[R:{row - start}]">
          <td id="table_tdrow_[C:1]-c[R:{row - start}]">
            <span id="table_col_1_ttxt-lb[R:{row - start}]" title="notice-{row}"></span>
          </td>
        </tr>'''
        for row in range(start, end + 1)
    )
    next_image = "tablebtn_next_on.gif" if has_next else "tablebtn_next_off.gif"
    return f'''<response><component><![CDATA[
      <span>{query_name}</span>
      <label id="table-lb3" class="tCount">{start} - {end}/{total}</label>
      <a id="table-ti7"><img id="table-ti7_img" src="{next_image}" /></a>
      <div id="table_ttrow_[C:1]_ttitle-lb">通報號</div>
      {rows}
    ]]></component></response>'''


def _empty_page(query_name: str) -> str:
    return f"<span>{query_name}</span><message>沒有要顯示的列。</message>"


def _run_with_responses(
    monkeypatch: pytest.MonkeyPatch, responses: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    client = SimpleNamespace(state=STATE)
    query = UnprocessedFaultNoticeQuery(client)
    calls: list[dict[str, Any]] = []
    response_iterator = iter(responses)

    monkeypatch.setattr(query, "_load_fault_notice_app", lambda: STATE)

    def fake_post_event(**kwargs: Any) -> str:
        calls.append(kwargs)
        return next(response_iterator)

    monkeypatch.setattr(query, "_post_event", fake_post_event)
    return query.run(), calls


def _secondary_selected_responses(
    *,
    secondary_first_page: str,
    additional_pages: list[str] | None = None,
) -> list[str]:
    return [
        MENU_RESPONSE,
        _page(1, 2, 2, query_name=QUERY_NAME, has_next=False),
        MENU_RESPONSE,
        secondary_first_page,
        *(additional_pages or []),
    ]


def test_run_selects_secondary_query_when_it_has_more_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run_with_responses(
        monkeypatch,
        _secondary_selected_responses(
            secondary_first_page=_page(
                1,
                3,
                3,
                query_name=SECONDARY_QUERY_NAME,
                has_next=False,
            )
        ),
    )

    assert result["query_name"] == SECONDARY_QUERY_NAME
    assert result["count"] == 3
    assert [calls[1]["value"], calls[3]["value"]] == [
        QUERY_MENU_VALUE,
        SECONDARY_QUERY_MENU_VALUE,
    ]
    assert [call["xhr_seq"] for call in calls] == [1, 2, 3, 4]


def test_run_reselects_primary_query_when_it_has_more_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run_with_responses(
        monkeypatch,
        [
            MENU_RESPONSE,
            _page(1, 3, 3, query_name=QUERY_NAME, has_next=False),
            MENU_RESPONSE,
            _page(
                1,
                2,
                2,
                query_name=SECONDARY_QUERY_NAME,
                has_next=False,
            ),
            MENU_RESPONSE,
            _page(1, 3, 3, query_name=QUERY_NAME, has_next=False),
        ],
    )

    assert result["query_name"] == QUERY_NAME
    assert result["count"] == 3
    assert [calls[index]["value"] for index in (1, 3, 5)] == [
        QUERY_MENU_VALUE,
        SECONDARY_QUERY_MENU_VALUE,
        QUERY_MENU_VALUE,
    ]
    assert [call["xhr_seq"] for call in calls] == [1, 2, 3, 4, 5, 6]


def test_run_prefers_primary_query_when_counts_are_equal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run_with_responses(
        monkeypatch,
        [
            MENU_RESPONSE,
            _page(1, 2, 2, query_name=QUERY_NAME, has_next=False),
            MENU_RESPONSE,
            _page(
                1,
                2,
                2,
                query_name=SECONDARY_QUERY_NAME,
                has_next=False,
            ),
            MENU_RESPONSE,
            _page(1, 2, 2, query_name=QUERY_NAME, has_next=False),
        ],
    )

    assert result["query_name"] == QUERY_NAME
    assert result["count"] == 2
    assert calls[5]["value"] == QUERY_MENU_VALUE


def test_run_collects_selected_primary_twenty_plus_two_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run_with_responses(
        monkeypatch,
        [
            MENU_RESPONSE,
            _page(1, 20, 22, query_name=QUERY_NAME, has_next=True),
            MENU_RESPONSE,
            _page(
                1,
                10,
                10,
                query_name=SECONDARY_QUERY_NAME,
                has_next=False,
            ),
            MENU_RESPONSE,
            _page(1, 20, 22, query_name=QUERY_NAME, has_next=True),
            _page(21, 22, 22, query_name=QUERY_NAME, has_next=False),
        ],
    )

    assert result["count"] == 22
    assert len(result["records"]) == 22
    assert calls[-1]["target_id"] == "table-ti7"
    assert calls[-1]["current_focus"] == "table-ti7"
    assert calls[-1]["value"] == "true"
    assert calls[-1]["xhr_seq"] == 7


def test_run_keeps_paging_selected_secondary_and_increments_xhr_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run_with_responses(
        monkeypatch,
        _secondary_selected_responses(
            secondary_first_page=_page(
                1,
                2,
                5,
                query_name=SECONDARY_QUERY_NAME,
                has_next=True,
            ),
            additional_pages=[
                _page(
                    3,
                    4,
                    5,
                    query_name=SECONDARY_QUERY_NAME,
                    has_next=True,
                ),
                _page(
                    5,
                    5,
                    5,
                    query_name=SECONDARY_QUERY_NAME,
                    has_next=False,
                ),
            ],
        ),
    )

    assert result["count"] == 5
    assert [call["xhr_seq"] for call in calls[-2:]] == [5, 6]


def test_run_rejects_non_contiguous_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="不連續"):
        _run_with_responses(
            monkeypatch,
            _secondary_selected_responses(
                secondary_first_page=_page(
                    1,
                    2,
                    5,
                    query_name=SECONDARY_QUERY_NAME,
                    has_next=True,
                ),
                additional_pages=[
                    _page(
                        4,
                        5,
                        5,
                        query_name=SECONDARY_QUERY_NAME,
                        has_next=False,
                    )
                ],
            ),
        )


def test_run_rejects_total_change_between_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(MMISClientError, match="總筆數改變"):
        _run_with_responses(
            monkeypatch,
            _secondary_selected_responses(
                secondary_first_page=_page(
                    1,
                    2,
                    5,
                    query_name=SECONDARY_QUERY_NAME,
                    has_next=True,
                ),
                additional_pages=[
                    _page(
                        3,
                        4,
                        6,
                        query_name=SECONDARY_QUERY_NAME,
                        has_next=True,
                    )
                ],
            ),
        )


def test_run_rejects_missing_next_page(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="找不到下一頁"):
        _run_with_responses(
            monkeypatch,
            _secondary_selected_responses(
                secondary_first_page=_page(
                    1,
                    2,
                    5,
                    query_name=SECONDARY_QUERY_NAME,
                    has_next=False,
                )
            ),
        )


def test_run_accepts_empty_tie_and_prefers_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls = _run_with_responses(
        monkeypatch,
        [
            MENU_RESPONSE,
            _empty_page(QUERY_NAME),
            MENU_RESPONSE,
            _empty_page(SECONDARY_QUERY_NAME),
            MENU_RESPONSE,
            _empty_page(QUERY_NAME),
        ],
    )

    assert result["query_name"] == QUERY_NAME
    assert result["count"] == 0
    assert result["records"] == []
    assert len(calls) == 6


def test_run_rejects_query_response_without_selected_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(MMISClientError, match="未確認"):
        _run_with_responses(
            monkeypatch,
            [MENU_RESPONSE, "<div>非預期查詢</div>"],
        )
