import json
from types import SimpleNamespace
from pathlib import Path
from urllib.parse import parse_qsl

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.atp_reader import ATP_ANALYSIS_FIELDS, FaultNoticeATPAnalysisReader
from mmis_connector.fault_notices.atp_writer import (
    ATPAnalysisAlreadyFilled, FaultNoticeATPAnalysisWriter,
)
from mmis_connector.parser import parse_labeled_inputs, parse_labeled_input_targets


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
NOTICE = "1151019-10"
VALUES = {field: field + "選項" for field in ATP_ANALYSIS_FIELDS}
RECORDING = Path(r"C:\Docker\maximoFlowRecorder\recordings\2026-10-28_nter-atp-fault-analysis")


def _inputs(current=None):
    current = current or {field: "" for field in ATP_ANALYSIS_FIELDS}
    return "".join(
        f'<label for="field-{index}">{field}:</label>'
        f'<input id="field-{index}" value="{current[field]}">'
        for index, field in enumerate(ATP_ANALYSIS_FIELDS)
    )


def _writer(monkeypatch, *, current=None, saved="BMXAA4205I", confirmed=None):
    writer = FaultNoticeATPAnalysisWriter(SimpleNamespace(state=STATE))
    detail = ('<img alt="ATP故障： 已勾選" src="cb_checkedreadonly.gif" '
              'checked="checked">'
              '<li id="analysis-tab" ctype="tab"><a title="故障分析"></a></li>')
    monkeypatch.setattr(writer, "_load_exact_detail", lambda notice: (STATE, detail))
    tabs = iter(('<li id="atp-tab" ctype="tab"><a title="故障分析-ATP"></a></li>',
                 _inputs(current)))
    tab_calls = []
    monkeypatch.setattr(writer, "_post_event", lambda **kwargs: tab_calls.append(kwargs) or next(tabs))
    posts = []
    monkeypatch.setattr(writer.events, "post", lambda **kwargs: posts.append(kwargs))
    monkeypatch.setattr(writer.events, "post_events", lambda **kwargs: posts.append(kwargs) or saved)
    monkeypatch.setattr(FaultNoticeATPAnalysisReader, "run",
                        lambda self, notice: {"analysis": confirmed if confirmed is not None else VALUES})
    return writer, tab_calls, posts


def test_writer_sends_recorded_event_order_and_reads_back(monkeypatch):
    writer, tabs, posts = _writer(monkeypatch)
    writer.run(NOTICE, VALUES)
    assert [call["target_id"] for call in tabs] == ["analysis-tab", "atp-tab"]
    assert [(post["event_type"], post["target_id"], post["value"])
            for post in posts[:2]] == [
        ("setvalue", "field-0", VALUES["故障要因"]),
        ("setvalue", "field-1", VALUES["故障因子"]),
    ]
    assert [post["current_focus"] for post in posts] == [
        "field-1", "field-2", "field-2",
    ]
    assert posts[2]["events"] == [
        ("setvalue", "field-2", VALUES["故障項目"]),
        ("click", "toolactions_SAVE-tbb", ""),
    ]


def test_writer_refuses_partially_filled_atp_without_post(monkeypatch):
    writer, _, posts = _writer(monkeypatch, current={
        **{field: "" for field in ATP_ANALYSIS_FIELDS}, "故障要因": "人工選項",
    })
    with pytest.raises(ATPAnalysisAlreadyFilled):
        writer.run(NOTICE, VALUES)
    assert posts == []


@pytest.mark.parametrize("saved,confirmed,message", [
    ("<server_response/>", None, "儲存結果不明"),
    ("BMXAA4205I", {**VALUES, "故障項目": "其他選項"}, "內容不符"),
])
def test_writer_requires_save_confirmation_and_readback(
    monkeypatch, saved, confirmed, message,
):
    writer, _, _ = _writer(monkeypatch, saved=saved, confirmed=confirmed)
    with pytest.raises(MMISClientError, match=message):
        writer.run(NOTICE, VALUES)


@pytest.mark.skipif(not (RECORDING / "raw.har").exists(), reason="ATP 錄製不在本機")
def test_recording_confirms_dynamic_targets_save_and_final_values():
    entries = json.loads((RECORDING / "raw.har").read_text(encoding="utf-8"))["log"]["entries"]
    tab_response = entries[356]["response"]["content"]["text"]
    targets = parse_labeled_input_targets(
        tab_response, field_names=ATP_ANALYSIS_FIELDS, context_name="ATP故障分析"
    )
    assert all(not value for value in parse_labeled_inputs(
        tab_response, field_names=ATP_ANALYSIS_FIELDS, context_name="ATP故障分析"
    ).values())
    events = [event for index in (359, 361, 363) for event in json.loads(
        dict(parse_qsl(entries[index]["request"]["postData"]["text"]))["events"]
    )]
    assert [(event["type"], event["targetId"]) for event in events] == [
        ("setvalue", targets["故障要因"]),
        ("setvalue", targets["故障因子"]),
        ("setvalue", targets["故障項目"]),
        ("click", "toolactions_SAVE-tbb"),
    ]
    assert [dict(parse_qsl(entries[index]["request"]["postData"]["text"]))["currentfocus"]
            for index in (359, 361, 363)] == [
        targets["故障因子"], targets["故障項目"], targets["故障項目"],
    ]
    assert "BMXAA4205I" in entries[363]["response"]["content"]["text"]
    final_dom = next((RECORDING / "dom").glob("*.html")).read_text(encoding="utf-8")
    final_values = parse_labeled_inputs(
        final_dom, field_names=ATP_ANALYSIS_FIELDS, context_name="ATP故障分析"
    )
    assert [event["value"] for event in events[:3]] == list(final_values.values())
