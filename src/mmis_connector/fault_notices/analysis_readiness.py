"""Optional AI check for accident-related follow-up work-order records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openai import OpenAI

from ..auth import MMISClientError
from .ai_analysis import OpenAIAnalysisConfig, ROOT, _request


PROMPT_PATH = ROOT / "prompts" / "fault_analysis_readiness" / "system_prompt.md"
SCHEMA = {
    "type": "object",
    "properties": {"sufficient": {"type": "boolean"}},
    "required": ["sufficient"],
    "additionalProperties": False,
}


def load_prompt(path: Path = PROMPT_PATH) -> str:
    try:
        prompt = path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise MMISClientError(f"無法讀取資料充分性 Prompt: {path}") from exc
    if not prompt:
        raise MMISClientError(f"資料充分性 Prompt 不得為空: {path}")
    return prompt


def build_evidence(result: dict[str, Any]) -> str:
    materials = result["故障分析素材"]
    temporary = [
        order for order in materials["臨時檢修工單"]
        if str(order.get("工作單", "")).split("-")[1:2] in (["C1"], ["C2"])
    ]
    relevant = {
        "臨時檢修工單": temporary,
        "日檢工單": materials["日檢工單"],
        "定期檢修工單": materials["定期檢修工單"],
    }
    for kind, orders in relevant.items():
        for order in orders:
            if order.get("查詢狀態") == "失敗":
                raise MMISClientError(f"{kind} {order.get('工作單', '')} 查詢失敗，無法安全判斷資料充分性")
    analysis = result["故障分析"]
    evidence = {
        "事故現象": analysis.get("事故現象") or "",
        "第一優先": {
            "臨時檢修工單 C1/C2": temporary,
            "CA查修工單": [
                {"工作單": order.get("工作單"), "維修情形": order.get("維修情形")}
                for order in result.get("CA查修工單", [])
            ],
        },
        "第二優先": {
            "日檢工單 1A": materials["日檢工單"],
            "定期檢修工單 2A/3A": materials["定期檢修工單"],
        },
    }
    return json.dumps(evidence, ensure_ascii=False, indent=2)


def parse_response(raw: str) -> bool:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    try:
        parsed = json.loads(raw, object_pairs_hook=unique_object)
    except (TypeError, ValueError) as exc:
        raise MMISClientError("AI 資料充分性回應不是有效 JSON") from exc
    if not isinstance(parsed, dict) or set(parsed) != {"sufficient"} or type(parsed["sufficient"]) is not bool:
        raise MMISClientError("AI 資料充分性回應必須是單一 boolean 欄位")
    return parsed["sufficient"]


def check_analysis_readiness(result: dict[str, Any], *, client: OpenAI | None = None) -> bool:
    system = load_prompt()
    user = build_evidence(result)
    config = OpenAIAnalysisConfig.from_env()
    client = client or OpenAI(api_key=config.api_key, timeout=config.timeout_seconds, max_retries=0)
    raw = _request(client, config, system, user, schema=SCHEMA, name="fault_analysis_readiness")
    return parse_response(raw)
