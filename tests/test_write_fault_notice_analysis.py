from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.analysis_writer import (
    FaultNoticeAnalysisWriter, WRITE_FIELDS,
)
from mmis_connector.fault_notices.reader import FaultNoticeAnalysisReader


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
NOTICE = "1151019-10"
VALUES = {field: field + "內容" for field in WRITE_FIELDS}


def _analysis(values=None):
    values = values or {field: "" for field in WRITE_FIELDS}
    return "".join(
        f'<label for="field-{index}">{field}:</label>'
        f'<textarea id="field-{index}">{values[field]}</textarea>'
        for index, field in enumerate(WRITE_FIELDS)
    )


def _writer(monkeypatch, *, saved="BMXAA4205I - 已儲存記錄。", confirmed=None,
            current=None):
    client = SimpleNamespace(state=STATE)
    writer = FaultNoticeAnalysisWriter(client)
    monkeypatch.setattr(writer, "_load_exact_detail",
                        lambda notice: (STATE, '<li id="tab" ctype="tab">'
                                        '<a title="故障分析">故障分析</a></li>'))
    monkeypatch.setattr(writer, "_post_event", lambda **kwargs: _analysis(current))
    posts = []
    monkeypatch.setattr(writer.events, "post", lambda **kwargs: posts.append(kwargs))
    monkeypatch.setattr(writer.events, "post_events",
                        lambda **kwargs: posts.append(kwargs) or saved)
    monkeypatch.setattr(FaultNoticeAnalysisReader, "run",
                        lambda self, notice: {"analysis": confirmed or VALUES})
    return writer, posts


def test_write_uses_dynamic_targets_and_verifies_saved_fields(monkeypatch):
    writer, posts = _writer(monkeypatch)
    writer.run(NOTICE, VALUES)
    assert [(post["event_type"], post["target_id"], post["value"])
            for post in posts[:2]] == [
        ("setvalue", "field-0", VALUES["故障原因"]),
        ("setvalue", "field-1", VALUES["處理情形"]),
    ]
    assert posts[2]["events"] == [
        ("setvalue", "field-2", VALUES["改善對策"]),
        ("click", "toolactions_SAVE-tbb", ""),
    ]


def test_write_preserves_existing_nonempty_analysis(monkeypatch):
    original = {**{field: "" for field in WRITE_FIELDS}, "故障原因": "人工原因"}
    confirmed = {**VALUES, "故障原因": "人工原因"}
    writer, posts = _writer(monkeypatch, current=original, confirmed=confirmed)
    writer.run(NOTICE, VALUES)
    assert posts[0]["value"] == "人工原因"


@pytest.mark.parametrize("saved,confirmed,message", [
    ("<server_response/>", None, "儲存結果不明"),
    ("BMXAA4205I", {**VALUES, "故障原因": "錯誤"}, "內容不符"),
])
def test_write_requires_save_and_readback(monkeypatch, saved, confirmed, message):
    writer, _ = _writer(monkeypatch, saved=saved, confirmed=confirmed)
    with pytest.raises(MMISClientError, match=message):
        writer.run(NOTICE, VALUES)
