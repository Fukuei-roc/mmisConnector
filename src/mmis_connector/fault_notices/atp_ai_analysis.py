"""Independent, read-only ATP classification of collected fault evidence."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from ..auth import MMISClientError
from .ai_analysis import FIELDS as GENERATED_FIELDS, OpenAIAnalysisConfig, ROOT, _request


OPTIONS_PATH = ROOT / "data" / "atp_fault_analysis_options.json"
PROMPT_PATH = ROOT / "prompts" / "atp_fault_analysis" / "prompt.md"
ATP_FIELDS = ("故障要因", "故障因子", "故障項目")
ATP_SCHEMA = {
    "type": "object",
    "properties": {field: {"type": "string"} for field in ATP_FIELDS},
    "required": list(ATP_FIELDS),
    "additionalProperties": False,
}


def load_options(path: Path = OPTIONS_PATH) -> list[dict[str, Any]]:
    """Load a completed MMIS export; never infer missing branches."""
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise MMISClientError(f"無法載入 ATP 合法選項：{path}") from exc
    if not isinstance(document, dict) or document.get("traversal_status") != "completed" or document.get("errors"):
        raise MMISClientError("ATP 合法選項檔並非完整遍歷結果")
    causes = document.get("fault_causes")
    if not isinstance(causes, list) or not causes:
        raise MMISClientError("ATP 合法選項檔缺少故障要因")

    def check_nodes(nodes: list[Any], child: str | None, level: str) -> None:
        seen: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get("name"), str) or not node["name"]:
                raise MMISClientError(f"ATP 合法選項檔的{level}格式無效")
            if node["name"] in seen:
                raise MMISClientError(f"ATP 合法選項檔的{level}同層名稱重複")
            seen.add(node["name"])
            if child is not None:
                descendants = node.get(child)
                if not isinstance(descendants, list):
                    raise MMISClientError(f"ATP 合法選項檔的{level}下層資料不完整")
                check_nodes(descendants, "items" if child == "factors" else None,
                            "故障因子" if child == "factors" else "故障項目")

    check_nodes(causes, "factors", "故障要因")
    return causes


def prepare_evidence(result: dict[str, Any]) -> dict[str, Any]:
    """Reuse collected MMIS data while excluding MMIS labels and AI conclusions."""
    evidence = copy.deepcopy(result)
    evidence.pop("ATP故障分析", None)
    evidence.pop("ATP故障分析_AI建議", None)
    evidence.pop("ATP故障分析_AI建議錯誤", None)
    evidence.pop("結案狀態檢查", None)
    analysis = evidence.get("故障分析")
    if analysis is not None:
        if not isinstance(analysis, dict):
            raise MMISClientError("MMIS 故障分析欄位格式無效")
        for field in GENERATED_FIELDS:
            analysis.pop(field, None)
    return evidence


def build_prompt(result: dict[str, Any], causes: list[dict[str, Any]], template: str) -> str:
    values = {
        "FAULT_EVIDENCE": json.dumps(prepare_evidence(result), ensure_ascii=False, indent=2),
        "ATP_OPTIONS": json.dumps(causes, ensure_ascii=False, indent=2),
    }
    if any("{{" + marker + "}}" not in template for marker in values):
        raise MMISClientError("ATP Prompt 缺少必要佔位符")
    if set(re.findall(r"\{\{([^{}]+)\}\}", template)) != set(values):
        raise MMISClientError("ATP Prompt 包含不支援的佔位符")
    return re.sub(r"\{\{(FAULT_EVIDENCE|ATP_OPTIONS)\}\}",
                  lambda match: values[match.group(1)], template)


def validate_classification(raw: str, causes: list[dict[str, Any]]) -> dict[str, str]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (TypeError, ValueError) as exc:
        raise MMISClientError("ATP AI 分類不是有效的 JSON") from exc
    if not isinstance(value, dict) or set(value) != set(ATP_FIELDS):
        raise MMISClientError("ATP AI 分類必須恰好包含三個指定欄位")
    if any(not isinstance(value[field], str) for field in ATP_FIELDS):
        raise MMISClientError("ATP AI 分類欄位必須為字串")
    cause = next((node for node in causes if node["name"] == value["故障要因"]), None)
    if cause is None:
        raise MMISClientError("ATP AI 故障要因不是合法選項")
    factors = cause["factors"]
    if not factors:
        if value["故障因子"] == value["故障項目"] == "":
            return value
        raise MMISClientError("ATP AI 分類的故障要因沒有下層選項")
    factor = next((node for node in factors if node["name"] == value["故障因子"]), None)
    if factor is None:
        raise MMISClientError("ATP AI 故障因子不屬於故障要因")
    items = factor["items"]
    if not items:
        if value["故障項目"] == "":
            return value
        raise MMISClientError("ATP AI 分類的故障因子沒有下層選項")
    if not any(node["name"] == value["故障項目"] for node in items):
        raise MMISClientError("ATP AI 故障項目不屬於故障因子")
    return value


def analyze_atp_fault(result: dict[str, Any], *, client: OpenAI | None = None) -> dict[str, str]:
    causes = load_options()
    try:
        template = PROMPT_PATH.read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError) as exc:
        raise MMISClientError("無法讀取 ATP 分類 Prompt") from exc
    if not template:
        raise MMISClientError("ATP 分類 Prompt 不得為空")
    config = OpenAIAnalysisConfig.from_env()
    client = client or OpenAI(api_key=config.api_key, timeout=config.timeout_seconds, max_retries=0)
    options_only = [{"name": cause["name"], "factors": [
        {"name": factor["name"], "items": [item["name"] for item in factor["items"]]}
        for factor in cause["factors"]]} for cause in causes]
    user = build_prompt(result, options_only, template)
    for attempt in range(2):
        raw = _request(client, config, "你是 ATP 故障分類助理。只回傳符合指定 JSON schema 的分類。", user,
                       schema=ATP_SCHEMA, name="atp_fault_classification")
        try:
            return validate_classification(raw, causes)
        except MMISClientError as exc:
            if attempt:
                raise MMISClientError(f"ATP AI 分類驗證失敗：{exc}") from exc
            user += "\n\n上次分類未通過合法選項路徑驗證。請重新依選項樹選擇完整且合法的路徑。"
    raise AssertionError("unreachable")
