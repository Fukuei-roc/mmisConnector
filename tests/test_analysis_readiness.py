from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError

from mmis_connector.auth import MMISClientError
from mmis_connector.fault_notices import analysis_readiness as readiness
from mmis_connector.fault_notices import ai_analysis
from tools.mmis_development import query_fault_notice_full_detail as tool


@pytest.fixture
def notice():
    return {
        "通報號": "1150910-14", "是ATP故障": False,
        "段修工單": [], "CA查修工單": [],
        "故障分析": {"事故現象": "2193次於彰化站，EM9351車下異味，列車停駛。", "處理概況": "", "故障原因": "", "處理情形": "", "改善對策": ""},
        "ATP故障分析": None,
        "故障分析素材": {"臨時檢修工單": [], "日檢工單": [], "定期檢修工單": []},
    }


def _mock_tool(monkeypatch, notice):
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda _: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool, "FaultNoticeFullDetailReader", lambda _: SimpleNamespace(run=lambda number: copy.deepcopy(notice)))
    monkeypatch.setattr(tool, "collect_analysis_materials", lambda client, orders: copy.deepcopy(notice["故障分析素材"]))


def test_modes_and_json_contract(monkeypatch, notice):
    _mock_tool(monkeypatch, notice)
    calls = []
    monkeypatch.setattr(tool, "analyze_fault_notice", lambda result: calls.append("analysis") or {"故障原因": "原因", "處理情形": "處理", "改善對策": "對策"})
    monkeypatch.setattr(tool, "check_analysis_readiness", lambda result: calls.append("readiness") or True)
    default = tool.execute([notice["通報號"]])
    assert calls == []
    analysis = tool.execute([notice["通報號"], "--ai-analysis"])
    assert calls == ["analysis"]
    checked = tool.execute([notice["通報號"], "--check-analysis-readiness"])
    assert calls == ["analysis", "readiness"]
    for result, expected in ((default, None), (analysis, None), (checked, True)):
        checks = result["結案狀態檢查"]
        assert next(iter(checks)) == "Sufficient Data for Fault Analysis"
        assert checks["Sufficient Data for Fault Analysis"] is expected
        assert json.loads(json.dumps(result, ensure_ascii=False))["結案狀態檢查"] == checks
        assert set(notice) <= set(result)
    assert default["故障分析"] == checked["故障分析"] == notice["故障分析"]
    assert analysis["故障分析"]["故障原因"] == "原因"


@pytest.mark.parametrize("flag", [None, "--ai-analysis"])
def test_other_modes_never_load_readiness_prompt(monkeypatch, notice, flag):
    _mock_tool(monkeypatch, notice)
    monkeypatch.setattr(readiness, "load_prompt", lambda: pytest.fail("readiness prompt loaded"))
    monkeypatch.setattr(tool, "analyze_fault_notice", lambda result: {"故障原因": "原因", "處理情形": "處理", "改善對策": "對策"})
    tool.execute([notice["通報號"]] + ([flag] if flag else []))


def test_mutually_exclusive_flags_are_rejected_before_login(monkeypatch, notice, capsys):
    monkeypatch.setattr(tool, "MMISSession", lambda _: pytest.fail("login"))
    assert tool.main([notice["通報號"], "--ai-analysis", "--check-analysis-readiness"]) != 0
    assert json.loads(capsys.readouterr().out)["success"] is False


@pytest.mark.parametrize("kind,number,field,record", [
    ("臨時檢修工單", "115-C1-1", "維修程序概況", "派員會同廠商勘查 EM9351 齒輪箱"),
    ("臨時檢修工單", "115-C2-1", "維修程序概況", "更換 EM9351 齒輪箱後試車"),
    ("CA查修工單", "115-CA-1", "維修情形", "檢查 EM9351 第3軸齒輪箱發現漏油"),
    ("日檢工單", "115-1A-1", "檢修記錄", "檢查 EM9351 第3軸齒輪箱"),
    ("定期檢修工單", "115-2A-1", "維修情形", "調整 EM9351 齒輪箱"),
    ("定期檢修工單", "115-3A-1", "維修情形", "更換 EM9351 齒輪箱"),
])
def test_evidence_contains_actual_followup_for_each_order_kind(monkeypatch, notice, kind, number, field, record):
    target = notice["CA查修工單"] if kind == "CA查修工單" else notice["故障分析素材"][kind]
    target.append({"工作單": number, field: record})
    evidence = readiness.build_evidence(notice)
    assert record in evidence
    assert evidence.index("第一優先") < evidence.index("第二優先")
    assert "工單結案" not in evidence
    monkeypatch.setattr(ai_analysis.OpenAIAnalysisConfig, "from_env", lambda: ai_analysis.OpenAIAnalysisConfig("fake", "model", "low", 1000, 1))
    def create(**kwargs):
        assert record in kwargs["input"][1]["content"]
        return SimpleNamespace(status="completed", output_text='{"sufficient":true}')
    assert readiness.check_analysis_readiness(notice, client=SimpleNamespace(responses=SimpleNamespace(create=create))) is True


@pytest.mark.parametrize("content", [
    "2193次於彰化站，EM9351車下異味，列車停駛。",
    "工單結案",
    "其他設備例行保養完成",
    "待查",
    "",
])
def test_negative_evidence_is_passed_to_model_without_local_guess(monkeypatch, notice, content):
    notice["故障分析素材"]["臨時檢修工單"].append({"工作單": "115-C1-1", "維修程序概況": content})
    assert content in readiness.build_evidence(notice)
    monkeypatch.setattr(ai_analysis.OpenAIAnalysisConfig, "from_env", lambda: ai_analysis.OpenAIAnalysisConfig("fake", "model", "low", 1000, 1))
    def create(**kwargs):
        assert content in kwargs["input"][1]["content"]
        return SimpleNamespace(status="completed", output_text='{"sufficient":false}')
    assert readiness.check_analysis_readiness(notice, client=SimpleNamespace(responses=SimpleNamespace(create=create))) is False


def test_no_work_orders_can_return_false(monkeypatch, notice):
    monkeypatch.setattr(ai_analysis.OpenAIAnalysisConfig, "from_env", lambda: ai_analysis.OpenAIAnalysisConfig("fake", "model", "low", 1000, 1))
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(status="completed", output_text='{"sufficient":false}')))
    assert readiness.check_analysis_readiness(notice, client=client) is False


def test_ca_evidence_excludes_personnel_and_prior_analysis(notice):
    notice["CA查修工單"].append({"工作單": "115-CA-1", "維修情形": "檢查齒輪箱", "檢查人員": "敏感姓名"})
    notice["故障分析"]["處理概況"] = "舊處理概況"
    evidence = readiness.build_evidence(notice)
    assert "檢查齒輪箱" in evidence
    assert "敏感姓名" not in evidence
    assert "舊處理概況" not in evidence


@pytest.mark.parametrize("value", [True, False])
def test_structured_api_boolean(monkeypatch, notice, value):
    monkeypatch.setattr(ai_analysis.OpenAIAnalysisConfig, "from_env", lambda: ai_analysis.OpenAIAnalysisConfig("fake", "model", "low", 1000, 1))
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_text=json.dumps({"sufficient": value}))
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    assert readiness.check_analysis_readiness(notice, client=client) is value
    assert calls[0]["text"]["format"]["schema"]["properties"]["sufficient"]["type"] == "boolean"
    assert calls[0]["text"]["format"]["strict"] is True
    assert "故障原因" not in calls[0]["input"][1]["content"]


@pytest.mark.parametrize("raw", ["", "true", "false", "{}", '{"sufficient":"true"}', '{"sufficient":null}', '{"sufficient":1}', '{"sufficient":true,"reason":"x"}', '{"sufficient":true,"sufficient":false}', "```json\ntrue\n```"])
def test_invalid_response_is_error(raw):
    with pytest.raises(MMISClientError, match="AI 資料充分性"):
        readiness.parse_response(raw)


def test_invalid_ai_result_uses_json_error_contract(monkeypatch, notice, capsys):
    _mock_tool(monkeypatch, notice)
    monkeypatch.setattr(tool, "check_analysis_readiness", lambda result: readiness.parse_response('"false"'))
    assert tool.main([notice["通報號"], "--check-analysis-readiness"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["error"] == "MMISClientError"


def test_prompt_missing_and_blank(tmp_path):
    with pytest.raises(MMISClientError, match="無法讀取"):
        readiness.load_prompt(tmp_path / "missing.md")
    blank = tmp_path / "blank.md"
    blank.write_text(" \n", encoding="utf-8")
    with pytest.raises(MMISClientError, match="不得為空"):
        readiness.load_prompt(blank)


def test_prompt_exists_and_covers_semantic_rules():
    prompt = readiness.load_prompt()
    for phrase in ("C1", "C2", "CA", "1A", "2A", "3A", "事故現象", "後續", "無關", "結案", "true", "false"):
        assert phrase in prompt


def test_prompt_path_is_independent_of_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert readiness.load_prompt()


def test_failed_work_order_query_is_not_false(notice):
    notice["故障分析素材"]["日檢工單"].append({"工作單": "115-1A-1", "查詢狀態": "失敗"})
    with pytest.raises(MMISClientError, match="無法安全判斷"):
        readiness.build_evidence(notice)


def test_timeout_is_error(monkeypatch, notice):
    monkeypatch.setattr(ai_analysis.OpenAIAnalysisConfig, "from_env", lambda: ai_analysis.OpenAIAnalysisConfig("fake", "model", "low", 1000, 1))
    monkeypatch.setattr(ai_analysis.time, "sleep", lambda _: None)
    def timeout(**kwargs):
        raise APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    client = SimpleNamespace(responses=SimpleNamespace(create=timeout))
    with pytest.raises(MMISClientError, match="逾時"):
        readiness.check_analysis_readiness(notice, client=client)
