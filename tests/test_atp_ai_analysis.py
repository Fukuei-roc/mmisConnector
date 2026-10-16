import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError
from mmis_connector.fault_notices import atp_ai_analysis as atp
from tools.mmis_development import query_fault_notice_full_detail as tool
from tools.mmis_development import export_atp_fault_analysis_options as exporter_tool


VALID = {"故障要因": "非ATP故障", "故障因子": "非ATP故障", "故障項目": "地上設備故障"}


@pytest.fixture
def notice():
    return {
        "通報號": "1151012-36", "事故等級": "B", "發生日期": "2026/10/12",
        "車次": "123", "車組/車號": "EM9001", "是ATP故障": True,
        "ATP故障分析": {"故障要因": "設備故障", "故障因子": "01.MMI 操作面盤", "故障項目": "MMI操作面盤"},
        "段修工單": [], "CA查修工單": [{"工作單": "115-CA-1", "查修結果": "地上設備故障"}],
        "故障分析": {"事故現象": "ATP 異常", "處理概況": "重啟", "故障原因": "舊結論", "處理情形": "", "改善對策": ""},
    }


def test_real_options_and_duplicate_names():
    assert exporter_tool.OUTPUT == atp.OPTIONS_PATH
    causes = atp.load_options()
    assert len(causes) == 6
    assert sum(len(c["factors"]) for c in causes) == 23
    assert sum(len(f["items"]) for c in causes for f in c["factors"]) == 65
    assert atp.validate_classification(json.dumps(VALID, ensure_ascii=False), causes) == VALID
    assert atp.validate_classification(json.dumps({
        "故障要因": "不明原因", "故障因子": "異地重開正常", "故障項目": "返段測試正常"
    }, ensure_ascii=False), causes)


@pytest.mark.parametrize("value", [
    "not JSON", "{}", '{"故障要因":"非ATP故障","故障要因":"設備故障","故障因子":"非ATP故障","故障項目":"非ATP故障"}',
    json.dumps({**VALID, "故障要因": "不存在"}, ensure_ascii=False),
    json.dumps({**VALID, "故障因子": "01.MMI 操作面盤"}, ensure_ascii=False),
    json.dumps({**VALID, "故障項目": "車輛其他設備故障 "}, ensure_ascii=False),
    json.dumps({**VALID, "故障項目": 1}, ensure_ascii=False),
])
def test_rejects_bad_classification(value):
    with pytest.raises(MMISClientError):
        atp.validate_classification(value, atp.load_options())


def test_empty_branches_and_ambiguous_siblings(tmp_path: Path):
    path = tmp_path / "options.json"
    document = {"traversal_status": "completed", "errors": [], "fault_causes": [
        {"name": "甲", "factors": []},
        {"name": "乙", "factors": [{"name": "相同", "items": []}]},
        {"name": "丙", "factors": [{"name": "相同", "items": [{"name": "項目"}]}]},
    ]}
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    causes = atp.load_options(path)
    assert atp.validate_classification(json.dumps({"故障要因": "甲", "故障因子": "", "故障項目": ""}, ensure_ascii=False), causes)
    assert atp.validate_classification(json.dumps({"故障要因": "乙", "故障因子": "相同", "故障項目": ""}, ensure_ascii=False), causes)
    with pytest.raises(MMISClientError):
        atp.validate_classification(json.dumps({"故障要因": "乙", "故障因子": "相同", "故障項目": "項目"}, ensure_ascii=False), causes)
    document["fault_causes"][1]["factors"].append({"name": "相同", "items": []})
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(MMISClientError, match="同層名稱重複"):
        atp.load_options(path)
    path.unlink()
    with pytest.raises(MMISClientError, match="無法載入"):
        atp.load_options(path)


def test_prompt_uses_shared_raw_data_without_mmis_labels_or_ai_conclusions(notice):
    before = copy.deepcopy(notice)
    evidence = atp.prepare_evidence({**notice, "結案狀態檢查": {"ATP Fault Analysis Incomplete": False}})
    assert notice == before
    assert evidence["CA查修工單"] == notice["CA查修工單"]
    assert evidence["通報號"] == notice["通報號"]
    assert "ATP故障分析" not in evidence and "結案狀態檢查" not in evidence
    assert "故障原因" not in evidence["故障分析"]
    prompt = atp.build_prompt(notice, atp.load_options(), atp.PROMPT_PATH.read_text(encoding="utf-8"))
    assert "115-CA-1" in prompt and "01.MMI 操作面盤" in prompt  # legal option, not MMIS answer
    assert "舊結論" not in prompt
    assert '"ATP故障分析"' not in prompt
    notice["故障分析"]["事故現象"] = "literal {{ATP_OPTIONS}} marker"
    assert "literal {{ATP_OPTIONS}} marker" in atp.build_prompt(
        notice, [], "{{FAULT_EVIDENCE}}\n{{ATP_OPTIONS}}")


@pytest.mark.parametrize("flag,atp_value,classification", [
    (False, True, "full"), (False, True, "partial"), (False, True, "empty"),
    (True, False, "full"), (True, "true", "full"),
    (True, True, "full"), (True, True, "partial"), (True, True, "empty"),
])
def test_cli_trigger_matrix(monkeypatch, notice, flag, atp_value, classification):
    notice["是ATP故障"] = atp_value
    if classification == "partial":
        notice["ATP故障分析"]["故障項目"] = ""
    elif classification == "empty":
        notice["ATP故障分析"] = dict.fromkeys(atp.ATP_FIELDS, "")
    original = copy.deepcopy(notice["ATP故障分析"])
    calls = []
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda config: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool, "FaultNoticeFullDetailReader", lambda client: SimpleNamespace(run=lambda number: copy.deepcopy(notice)))
    monkeypatch.setattr(tool, "collect_analysis_materials", lambda client, orders: {"日檢工單": []})
    monkeypatch.setattr(tool, "analyze_fault_notice", lambda result: {"故障原因": "* 原因", "處理情形": "* 處理", "改善對策": "* 改善"})
    monkeypatch.setattr(tool, "analyze_atp_fault", lambda result: calls.append(copy.deepcopy(result)) or VALID)
    result = tool.execute(["1151012-36"] + (["--ai-analysis"] if flag else []))
    expected = flag and atp_value is True
    assert len(calls) == int(expected)
    assert result["ATP故障分析"] == original
    assert ("ATP故障分析_AI建議" in result) == expected
    if expected:
        assert result["ATP故障分析_AI建議"] == VALID
        assert result["ATP故障分析_AI建議"] != result["ATP故障分析"]
    assert ("故障分析素材" in result) and result["CA查修工單"] == notice["CA查修工單"]


def test_atp_failure_keeps_query_and_existing_ai(monkeypatch, notice):
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda config: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool, "FaultNoticeFullDetailReader", lambda client: SimpleNamespace(run=lambda number: copy.deepcopy(notice)))
    monkeypatch.setattr(tool, "collect_analysis_materials", lambda client, orders: {})
    monkeypatch.setattr(tool, "analyze_fault_notice", lambda result: {"故障原因": "* AI 原因", "處理情形": "* 處理", "改善對策": "* 改善"})
    monkeypatch.setattr(tool, "analyze_atp_fault", lambda result: (_ for _ in ()).throw(MMISClientError("ATP AI 分類驗證失敗")))
    result = tool.execute(["1151012-36", "--ai-analysis"])
    assert result["ATP故障分析"] == notice["ATP故障分析"]
    assert result["CA查修工單"] == notice["CA查修工單"]
    assert result["故障分析"]["故障原因"] == "* AI 原因"
    assert "ATP故障分析_AI建議" not in result
    assert "驗證失敗" in result["ATP故障分析_AI建議錯誤"]


def test_atp_api_retries_invalid_path_once(monkeypatch, notice):
    monkeypatch.setattr(atp.OpenAIAnalysisConfig, "from_env", lambda: atp.OpenAIAnalysisConfig("fake", "gpt-6-luna", "medium", 6000, 120))
    calls = []
    output = iter([json.dumps({**VALID, "故障項目": "虛構"}, ensure_ascii=False), json.dumps(VALID, ensure_ascii=False)])
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_text=next(output))
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    assert atp.analyze_atp_fault(notice, client=client) == VALID
    assert len(calls) == 2
    assert calls[0]["text"]["format"]["name"] == "atp_fault_classification"
    assert calls[0]["store"] is False
    assert '"ATP故障分析"' not in calls[0]["input"][1]["content"]


def test_atp_api_stops_after_second_invalid_path(monkeypatch, notice):
    monkeypatch.setattr(atp.OpenAIAnalysisConfig, "from_env", lambda: atp.OpenAIAnalysisConfig("fake", "gpt-6-luna", "medium", 6000, 120))
    calls = []
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(status="completed", output_text="{}")))
    with pytest.raises(MMISClientError, match="ATP AI 分類驗證失敗"):
        atp.analyze_atp_fault(notice, client=client)
    assert len(calls) == 2
