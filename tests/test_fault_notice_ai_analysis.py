import copy
import json
from types import SimpleNamespace

import pytest
import httpx
from openai import APITimeoutError, AuthenticationError, BadRequestError, InternalServerError, NotFoundError, RateLimitError

from mmis_connector.auth import MMISClientError
from mmis_connector.fault_notices import ai_analysis as ai
from tools.mmis_development import query_fault_notice_full_detail as tool


GOOD = {
    "故障原因": "* 接點接觸不良。",
    "處理情形": "* 已檢查接點並完成測試。",
    "改善對策": "* 維修面：\n  * 加強接點檢查。",
}


@pytest.fixture
def notice():
    return {
        "通報號": "1150910-14", "車組/車號": "EM9351",
        "段修工單": [{"工作單": "115-C1-1", "車組/車號": "EM9001"}],
        "CA查修工單": [{"工作單": "115-CA-1"}],
        "故障分析": {"事故現象": "停機", "處理概況": "檢查中", "故障原因": "舊結論", "其他欄": "保留"},
        "ATP故障分析": None,
        "故障分析素材": {
            "臨時檢修工單": [
                {"工作單": "115-C1-1", "車組/車號": "EM9001", "原因說明": "接點鬆動"},
                {"工作單": "115-C2-2", "車組/車號": "EM9351"},
            ],
            "日檢工單": [{"工作單": "115-1A-1", "檢修記錄": []}],
            "定期檢修工單": [],
        },
    }


def test_prompt_keeps_all_materials_without_prior_conclusions_or_vehicle_filter(notice):
    before = copy.deepcopy(notice)
    rendered = ai.build_user_prompt(notice, "{{事故現象}} {{處理概況}} {{MMIS_JSON}}")
    assert "舊結論" not in rendered
    assert "EM9001" in rendered and "EM9351" in rendered
    assert "115-C2-2" in rendered and "115-1A-1" in rendered
    assert "115-CA-1" in rendered
    assert notice == before


def test_merge_preserves_original_and_places_analysis_last(notice):
    merged = ai.merge_fault_analysis(notice, GOOD)
    assert list(merged)[-1] == "故障分析"
    assert merged["故障分析"] == {
        "事故現象": "停機", "處理概況": "檢查中", "故障原因": GOOD["故障原因"],
        "其他欄": "保留", "處理情形": GOOD["處理情形"], "改善對策": GOOD["改善對策"],
    }
    assert notice["故障分析"]["故障原因"] == "舊結論"
    assert ai.merge_fault_analysis({"故障分析": None}, GOOD)["故障分析"] == GOOD


@pytest.mark.parametrize("bad", [
    "not json", "```json\n{}\n```", json.dumps({"故障原因": "* a"}),
    json.dumps({**GOOD, "多餘": "* a"}, ensure_ascii=False),
    json.dumps({**GOOD, "故障原因": " "}, ensure_ascii=False),
    json.dumps({**GOOD, "故障原因": "* **粗體**"}, ensure_ascii=False),
    json.dumps({**GOOD, "故障原因": "- 錯誤列點"}, ensure_ascii=False),
    json.dumps({**GOOD, "改善對策": "* 維修面：\n * 縮排錯誤"}, ensure_ascii=False),
    json.dumps({**GOOD, "改善對策": "  * 缺少分類"}, ensure_ascii=False),
    json.dumps({**GOOD, "改善對策": "* 其他面：\n  * 測試。"}, ensure_ascii=False),
])
def test_validation_rejects_bad_output(bad):
    with pytest.raises(MMISClientError):
        ai.validate_analysis(bad)


def test_mock_api_flow_and_one_format_retry(monkeypatch, notice):
    monkeypatch.setattr(ai.OpenAIAnalysisConfig, "from_env", lambda: ai.OpenAIAnalysisConfig("fake", "gpt-6-astra", "high", 6000, 120))
    calls = []
    outputs = iter(["{}", json.dumps(GOOD, ensure_ascii=False)])

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_text=next(outputs))

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    generated = ai.analyze_fault_notice(notice, client=client)
    assert generated == GOOD
    assert len(calls) == 2
    assert calls[0]["text"]["format"]["strict"] is True
    assert calls[0]["store"] is False
    assert calls[0]["model"] == "gpt-6-astra"
    assert "舊結論" not in calls[0]["input"][1]["content"]
    assert "EM9001" in calls[0]["input"][1]["content"]


def test_missing_key_is_clear(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "ROOT", tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MMISClientError, match="OPENAI_API_KEY"):
        ai.OpenAIAnalysisConfig.from_env()


def test_default_model_and_effort_are_luna_medium(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "ROOT", tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_REASONING_EFFORT", raising=False)
    config = ai.OpenAIAnalysisConfig.from_env()
    assert (config.model, config.reasoning_effort) == ("gpt-6-luna", "medium")


def test_prompts_are_separate_and_loadable():
    system = ai._read_prompt("SystemPrompt.md")
    user = ai._read_prompt("UserPrompt.md")
    assert "{{事故現象}}" not in system
    assert all("{{" + key + "}}" in user for key in ("事故現象", "處理概況", "MMIS_JSON"))


def test_cli_without_flag_never_calls_ai(monkeypatch, notice):
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda config: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool, "FaultNoticeFullDetailReader", lambda client: SimpleNamespace(run=lambda number: copy.deepcopy(notice)))
    monkeypatch.setattr(tool, "collect_analysis_materials", lambda client, orders: notice["故障分析素材"])
    monkeypatch.setattr(tool, "analyze_fault_notice", lambda result: pytest.fail("unexpected paid API call"))
    assert tool.execute(["1150910-14"]) == notice


def test_cli_with_flag_adds_ai_analysis(monkeypatch, notice):
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda config: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool, "FaultNoticeFullDetailReader", lambda client: SimpleNamespace(run=lambda number: copy.deepcopy(notice)))
    monkeypatch.setattr(tool, "collect_analysis_materials", lambda client, orders: notice["故障分析素材"])
    monkeypatch.setattr(tool, "analyze_fault_notice", lambda result: GOOD)
    merged = tool.execute(["1150910-14", "--ai-analysis"])
    assert list(merged)[-1] == "故障分析"
    assert merged["故障分析"]["故障原因"] == GOOD["故障原因"]
    assert json.loads(json.dumps(merged, ensure_ascii=False)) == merged


def test_cli_stdout_is_one_json_document(monkeypatch, capsys, notice):
    monkeypatch.setattr(tool, "execute", lambda args: ai.merge_fault_analysis(notice, GOOD))
    assert tool.main(["1150910-14", "--ai-analysis"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["故障分析"]["故障原因"] == GOOD["故障原因"]
    assert captured.err == ""


def test_cli_full_flow_with_mock_mmis_and_mock_openai(monkeypatch, capsys, notice):
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda config: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool, "FaultNoticeFullDetailReader", lambda client: SimpleNamespace(run=lambda number: copy.deepcopy(notice)))
    monkeypatch.setattr(tool, "collect_analysis_materials", lambda client, orders: notice["故障分析素材"])
    monkeypatch.setattr(ai.OpenAIAnalysisConfig, "from_env", lambda: ai.OpenAIAnalysisConfig("fake", "gpt-6-astra", "high", 12000, 120))
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(status="completed", output_text=json.dumps(GOOD, ensure_ascii=False))

    monkeypatch.setattr(ai, "OpenAI", lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert tool.main(["1150910-14", "--ai-analysis"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["故障分析"]["事故現象"] == "停機"
    assert result["故障分析"]["故障原因"] == GOOD["故障原因"]
    assert list(result)[-1] == "故障分析"
    assert len(requests) == 1
    assert "舊結論" not in requests[0]["input"][1]["content"]


def _api_error(kind, status, body, headers=None):
    response = httpx.Response(status, request=httpx.Request("POST", "https://api.openai.com/v1/responses"), headers=headers)
    return kind("safe test error", response=response, body=body)


@pytest.mark.parametrize("error,expected,calls", [
    (_api_error(BadRequestError, 400, {"code": "model_not_found"}), "模型 ID", 1),
    (_api_error(NotFoundError, 404, {"code": "model_not_found"}), "模型 ID", 1),
    (_api_error(AuthenticationError, 401, {"code": "invalid_api_key"}), "Key 無效", 1),
    (_api_error(RateLimitError, 429, {"code": "insufficient_quota"}), "額度不足", 1),
    (_api_error(RateLimitError, 429, {"code": "rate_limit_exceeded"}), "速率限制", 3),
    (_api_error(InternalServerError, 503, {}), "HTTP 503", 3),
    (APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses")), "逾時", 3),
])
def test_api_errors_have_bounded_retry_and_safe_message(monkeypatch, error, expected, calls):
    seen = []
    monkeypatch.setattr(ai.time, "sleep", lambda seconds: None)

    def fail(**kwargs):
        seen.append(kwargs)
        raise error

    client = SimpleNamespace(responses=SimpleNamespace(create=fail))
    config = ai.OpenAIAnalysisConfig("secret", "gpt-6-astra", "high", 6000, 120)
    with pytest.raises(MMISClientError, match=expected) as caught:
        ai._request(client, config, "system", "user")
    assert len(seen) == calls
    assert "secret" not in str(caught.value)


def test_retry_after_is_respected(monkeypatch):
    delays = []
    monkeypatch.setattr(ai.time, "sleep", delays.append)
    error = _api_error(RateLimitError, 429, {"code": "rate_limit_exceeded"}, {"retry-after": "3"})
    responses = iter([error, SimpleNamespace(status="completed", output_text=json.dumps(GOOD, ensure_ascii=False))])

    def create(**kwargs):
        item = next(responses)
        if isinstance(item, Exception):
            raise item
        return item

    config = ai.OpenAIAnalysisConfig("secret", "gpt-6-astra", "high", 6000, 120)
    assert ai._request(SimpleNamespace(responses=SimpleNamespace(create=create)), config, "system", "user")
    assert delays == [3.0]
