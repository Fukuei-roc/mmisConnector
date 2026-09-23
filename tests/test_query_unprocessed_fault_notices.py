from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.query_unprocessed_fault_notices import (
    QUERY_NAME,
    UnprocessedFaultNoticeQuery,
)


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")


def _page(start: int, end: int, total: int, *, has_next: bool) -> str:
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
      <span>{QUERY_NAME}</span>
      <label id="table-lb3" class="tCount">{start} - {end}/{total}</label>
      <a id="table-ti7"><img id="table-ti7_img" src="{next_image}" /></a>
      <div id="table_ttrow_[C:1]_ttitle-lb">通報號</div>
      {rows}
    ]]></component></response>'''


def _run_with_pages(
    monkeypatch: pytest.MonkeyPatch, pages: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    client = SimpleNamespace(state=STATE)
    query = UnprocessedFaultNoticeQuery(client)
    calls: list[dict[str, Any]] = []
    responses = iter(["<div>mainrec_menus</div>", *pages])

    monkeypatch.setattr(query, "_load_fault_notice_app", lambda: STATE)

    def fake_post_event(**kwargs: Any) -> str:
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(query, "_post_event", fake_post_event)
    return query.run(), calls


def test_run_collects_recorded_twenty_plus_two_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    result, calls = _run_with_pages(
        monkeypatch,
        [_page(1, 20, 22, has_next=True), _page(21, 22, 22, has_next=False)],
    )

    assert result["count"] == 22
    assert len(result["records"]) == 22
    assert calls[-1]["target_id"] == "table-ti7"
    assert calls[-1]["current_focus"] == "table-ti7"
    assert calls[-1]["value"] == "true"
    assert calls[-1]["xhr_seq"] == 3


def test_run_keeps_paging_and_increments_xhr_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    result, calls = _run_with_pages(
        monkeypatch,
        [
            _page(1, 2, 5, has_next=True),
            _page(3, 4, 5, has_next=True),
            _page(5, 5, 5, has_next=False),
        ],
    )

    assert result["count"] == 5
    assert [call["xhr_seq"] for call in calls[-2:]] == [3, 4]


def test_run_rejects_non_contiguous_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="不連續"):
        _run_with_pages(
            monkeypatch,
            [_page(1, 2, 5, has_next=True), _page(4, 5, 5, has_next=False)],
        )


def test_run_rejects_total_change_between_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="總筆數改變"):
        _run_with_pages(
            monkeypatch,
            [_page(1, 2, 5, has_next=True), _page(3, 4, 6, has_next=True)],
        )


def test_run_rejects_missing_next_page(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="找不到下一頁"):
        _run_with_pages(monkeypatch, [_page(1, 2, 5, has_next=False)])


def test_run_accepts_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    empty_response = f"<span>{QUERY_NAME}</span><message>沒有要顯示的列。</message>"

    result, calls = _run_with_pages(monkeypatch, [empty_response])

    assert result["count"] == 0
    assert result["records"] == []
    assert len(calls) == 2
