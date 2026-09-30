from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.reader import (
    ANALYSIS_FIELDS,
    FaultNoticeAnalysisReader,
    normalize_fault_notice,
)


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-09-30_query-fault-notice-analysis\dom"
    r"\2026-09-30T064859-451.html"
)


def _list_page() -> str:
    return '<span id="notice_ttrow_[C:14]_ttitle-lb">通報號</span>'


def _filter_result(notices: list[str]) -> str:
    headers = _list_page()
    if not notices:
        return headers + "<message>沒有要顯示的列。</message>"
    rows = "".join(
        '<tr id="notice_tbod_tdrow-tr[R:{row}]">'
        '<td id="notice_tdrow_[C:14]-c[R:{row}]">'
        '<span id="notice_tdrow_[C:14]_ttxt-lb[R:{row}]" '
        'title="{notice}">{notice}</span></td></tr>'.format(
            row=row, notice=notice
        )
        for row, notice in enumerate(notices)
    )
    return (
        headers
        + f'<label id="notice-lb3" class="tCount">1 - {len(notices)}/{len(notices)}</label>'
        + rows
    )


def _detail_page() -> str:
    return (
        '<li id="analysis-tab" ctype="tab">'
        '<a title="故障分析">故障分析</a></li>'
    )


def _analysis_page(values: dict[str, str] | None = None) -> str:
    actual = values or {field: f"{field}內容" for field in ANALYSIS_FIELDS}
    return "".join(
        f'<label for="field-{index}">{field}:</label>'
        f'<textarea id="field-{index}">{actual[field]}</textarea>'
        for index, field in enumerate(ANALYSIS_FIELDS)
    )


def _run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    notices: list[str] | None = None,
    analysis_response: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    client = SimpleNamespace(state=STATE)
    client.refresh_state = lambda page_url: (STATE, _list_page())
    reader = FaultNoticeAnalysisReader(client)
    monkeypatch.setattr(reader.events, "load_app", lambda **kwargs: STATE)

    multi_calls: list[dict[str, Any]] = []
    post_calls: list[dict[str, Any]] = []

    def fake_post_events(**kwargs: Any) -> str:
        multi_calls.append(kwargs)
        return _filter_result(
            ["1150828-12"] if notices is None else notices
        )

    responses = iter([_detail_page(), analysis_response or _analysis_page()])

    def fake_post_event(**kwargs: Any) -> str:
        post_calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "post_events", fake_post_events)
    monkeypatch.setattr(reader, "_post_event", fake_post_event)
    return reader.run(" 1150828-12 "), multi_calls, post_calls


@pytest.mark.parametrize(
    "value", ["", "1150828", "1150828-1", "115082-12", "A150828-12"]
)
def test_rejects_invalid_fault_notice_before_network(value: str) -> None:
    with pytest.raises(MMISClientError, match="通報號"):
        normalize_fault_notice(value)


def test_run_filters_exact_notice_and_reads_five_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, multi_calls, post_calls = _run(monkeypatch)

    assert multi_calls == [
        {
            "state": STATE,
            "current_focus": "notice_tfrow_[C:14]_txt-tb",
            "events": [
                ("setvalue", "notice_tfrow_[C:14]_txt-tb", "1150828-12"),
                ("filterrows", "notice_tbod_tfrow-tr", ""),
            ],
            "xhr_seq": 1,
        }
    ]
    assert [call["target_id"] for call in post_calls] == [
        "notice_tdrow_[C:14]_ttxt-lb[R:0]",
        "analysis-tab",
    ]
    assert result["fault_notice"] == "1150828-12"
    assert tuple(result["analysis"]) == ANALYSIS_FIELDS
    assert result["analysis"]["故障原因"] == "故障原因內容"


def test_run_preserves_empty_and_multiline_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {field: "" for field in ANALYSIS_FIELDS}
    values["處理情形"] = "第一行\n第二行"
    result, _, _ = _run(
        monkeypatch, analysis_response=_analysis_page(values)
    )

    assert result["analysis"]["故障原因"] == ""
    assert result["analysis"]["處理情形"] == "第一行\n第二行"


def test_run_rejects_missing_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="找不到故障通報"):
        _run(monkeypatch, notices=[])


def test_run_rejects_multiple_notices(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="不是唯一"):
        _run(monkeypatch, notices=["1150828-12", "1150828-12"])


def test_run_rejects_non_exact_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MMISClientError, match="不相符"):
        _run(monkeypatch, notices=["1150828-13"])


def test_run_rejects_missing_analysis_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _analysis_page().replace(
        '<label for="field-4">改善對策:</label>', ""
    )
    with pytest.raises(MMISClientError, match="改善對策"):
        _run(monkeypatch, analysis_response=response)


@pytest.mark.skipif(not RECORDED_DOM.is_file(), reason="local recording unavailable")
def test_recorded_dom_extracts_expected_analysis() -> None:
    from mmis_connector.parser import parse_labeled_textareas

    analysis = parse_labeled_textareas(
        RECORDED_DOM.read_text(encoding="utf-8"),
        field_names=ANALYSIS_FIELDS,
    )

    assert analysis["事故現象"] == "第7車(EM9284)疑似機油過熱，俟車輛返段詳查"
    assert analysis["處理概況"].startswith("第1207次(基隆~苗栗")
    assert analysis["故障原因"].startswith("* 第7車（EM9284）")
    assert "9月11日完成編組" in analysis["處理情形"]
    assert analysis["改善對策"].startswith("* 車輛面：")
