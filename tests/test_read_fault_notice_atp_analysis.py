from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.atp_reader import (
    ATP_ANALYSIS_FIELDS,
    FaultNoticeATPAnalysisReader,
)
from mmis_connector.parser import parse_atp_fault_checked, parse_labeled_inputs


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-02_query-atp-fault-analysis-linked-to-fault-notice\dom"
    r"\2026-10-02T052519-730.html"
)


def _detail(checked: bool) -> str:
    status = "已勾選" if checked else "未勾選"
    source = "cb_checkedreadonly.gif" if checked else "cb_uncheckedreadonly.gif"
    checked_attribute = ' checked="checked"' if checked else ""
    return (
        f'<img alt="ATP故障： {status}" src="{source}"{checked_attribute}>'
        '<li id="analysis-tab" ctype="tab"><a title="故障分析"></a></li>'
    )


def _analysis() -> str:
    return '<li id="atp-tab" ctype="tab"><a title="故障分析-ATP"></a></li>'


def _atp_values(empty: bool = False) -> str:
    requested = "".join(
        f'<label for="f{i}">{name}:</label>'
        f'<input id="f{i}" value="{name if not empty else ""}">'
        for i, name in enumerate(ATP_ANALYSIS_FIELDS)
    )
    excluded = "".join(
        f'<label for="x{i}">{name}:</label><input id="x{i}" value="其他值">'
        for i, name in enumerate(("故障點", "故障作為", "故障品處理", "故障項目備註"))
    )
    return requested + excluded


def test_reader_checks_atp_before_tabs_and_reads_all_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = SimpleNamespace(state=STATE)
    reader = FaultNoticeATPAnalysisReader(client)
    monkeypatch.setattr(
        "mmis_connector.fault_notices.atp_reader.FaultNoticeAnalysisReader._load_exact_detail",
        lambda self, notice: (STATE, _detail(True)),
    )
    calls: list[dict[str, Any]] = []
    responses = iter((_analysis(), _atp_values()))

    def post(**kwargs: Any) -> str:
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "post", post)
    result = reader.run("1150210-36")

    assert [call["target_id"] for call in calls] == ["analysis-tab", "atp-tab"]
    assert [call["xhr_seq"] for call in calls] == [3, 4]
    assert result["analysis"] == {name: name for name in ATP_ANALYSIS_FIELDS}


def test_unchecked_atp_stops_before_tab_events(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SimpleNamespace(state=STATE)
    reader = FaultNoticeATPAnalysisReader(client)
    monkeypatch.setattr(
        "mmis_connector.fault_notices.atp_reader.FaultNoticeAnalysisReader._load_exact_detail",
        lambda self, notice: (STATE, _detail(False)),
    )
    monkeypatch.setattr(
        reader.events, "post", lambda **kwargs: pytest.fail("unexpected tab click")
    )
    with pytest.raises(MMISClientError, match="此故障通報未勾選ATP故障"):
        reader.run("1150210-36")


def test_empty_values_and_missing_field() -> None:
    values = parse_labeled_inputs(
        _atp_values(empty=True),
        field_names=ATP_ANALYSIS_FIELDS,
        context_name="ATP故障分析",
    )
    assert all(value == "" for value in values.values())
    with pytest.raises(MMISClientError, match="故障項目"):
        parse_labeled_inputs(
            _atp_values().replace('<label for="f2">故障項目:</label>', ""),
            field_names=ATP_ANALYSIS_FIELDS,
            context_name="ATP故障分析",
        )


def test_checkbox_requires_explicit_consistent_state() -> None:
    assert parse_atp_fault_checked(_detail(True)) is True
    assert parse_atp_fault_checked(_detail(False)) is False
    with pytest.raises(MMISClientError, match="狀態不一致"):
        parse_atp_fault_checked(
            '<img alt="ATP故障： 已勾選" src="cb_uncheckedreadonly.gif" '
            'checked="checked">'
        )
    with pytest.raises(MMISClientError, match="唯一"):
        parse_atp_fault_checked('<img alt="其他故障： 已勾選">')


@pytest.mark.skipif(not RECORDED_DOM.is_file(), reason="local recording unavailable")
def test_recorded_atp_dom() -> None:
    markup = RECORDED_DOM.read_text(encoding="utf-8")
    analysis = parse_labeled_inputs(
        markup, field_names=ATP_ANALYSIS_FIELDS, context_name="ATP故障分析"
    )
    assert analysis["故障要因"] == "設備故障"
    assert analysis["故障因子"] == "04.BTM感應子傳輸模組"
    assert analysis["故障項目"] == "BTM感應子傳輸模組"
    assert tuple(analysis) == ATP_ANALYSIS_FIELDS
