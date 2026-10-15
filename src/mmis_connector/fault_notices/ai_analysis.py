"""Optional OpenAI analysis of an already collected fault notice."""

from __future__ import annotations

import copy
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import (
    APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError,
    BadRequestError, OpenAI, PermissionDeniedError, RateLimitError,
    NotFoundError,
)

from ..auth import MMISClientError


ROOT = Path(__file__).resolve().parents[3]
FIELDS = ("故障原因", "處理情形", "改善對策")
CATEGORIES = {"車輛面：", "維修面：", "運用面：", "管理面："}
SCHEMA = {
    "type": "object",
    "properties": {field: {"type": "string"} for field in FIELDS},
    "required": list(FIELDS),
    "additionalProperties": False,
}
PLACEHOLDERS = re.compile(r"\{\{(事故現象|處理概況|MMIS_JSON)\}\}")


@dataclass(frozen=True)
class OpenAIAnalysisConfig:
    api_key: str
    model: str
    reasoning_effort: str
    max_output_tokens: int
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "OpenAIAnalysisConfig":
        load_dotenv(ROOT / ".env", override=False)
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise MMISClientError("未設定 OPENAI_API_KEY；請在專案 .env 或系統環境變數中設定")
        model = os.getenv("OPENAI_MODEL", "gpt-6-luna").strip()
        effort = os.getenv("OPENAI_REASONING_EFFORT", "medium").strip()
        try:
            maximum = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "12000"))
            timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120"))
        except ValueError as exc:
            raise MMISClientError("OPENAI_MAX_OUTPUT_TOKENS 與 OPENAI_TIMEOUT_SECONDS 必須是數字") from exc
        if not model or effort not in {"low", "medium", "high", "xhigh", "max"}:
            raise MMISClientError("OPENAI_MODEL 或 OPENAI_REASONING_EFFORT 設定無效")
        if maximum < 1000 or timeout <= 0:
            raise MMISClientError("OPENAI_MAX_OUTPUT_TOKENS 至少為 1000，OPENAI_TIMEOUT_SECONDS 必須大於 0")
        return cls(key, model, effort, maximum, timeout)


def _read_prompt(name: str) -> str:
    try:
        prompt = (ROOT / name).read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise MMISClientError(f"無法讀取 {name}") from exc
    if not prompt:
        raise MMISClientError(f"{name} 不得為空")
    return prompt


def build_user_prompt(result: dict[str, Any], template: str) -> str:
    """Copy the complete MMIS result, excluding earlier generated conclusions."""
    evidence = copy.deepcopy(result)
    analysis = evidence.get("故障分析")
    if analysis is None:
        analysis = {}
    if not isinstance(analysis, dict):
        raise MMISClientError("MMIS 故障分析欄位格式無效")
    for field in FIELDS:
        analysis.pop(field, None)
    evidence["故障分析"] = analysis
    values = {
        "事故現象": analysis.get("事故現象") or "（原始資料未提供）",
        "處理概況": analysis.get("處理概況") or "（原始資料未提供）",
        "MMIS_JSON": json.dumps(evidence, ensure_ascii=False, indent=2),
    }
    for field in values:
        if "{{" + field + "}}" not in template:
            raise MMISClientError(f"UserPrompt.md 缺少 {{{{{field}}}}} 佔位符")
    unknown = set(re.findall(r"\{\{([^{}]+)\}\}", template)) - set(values)
    if unknown:
        raise MMISClientError("UserPrompt.md 包含不支援的佔位符")
    # Regex replacement is one pass: braces inside MMIS JSON are never interpreted.
    return PLACEHOLDERS.sub(lambda match: str(values[match.group(1)]), template)


def validate_analysis(raw: str) -> dict[str, str]:
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
        raise MMISClientError("AI 分析不是有效的 JSON") from exc
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise MMISClientError("AI 分析必須恰好包含三個指定欄位")
    for field in FIELDS:
        content = value[field]
        if not isinstance(content, str) or not content.strip():
            raise MMISClientError(f"AI 分析的「{field}」必須是非空字串")
        if "**" in content:
            raise MMISClientError(f"AI 分析的「{field}」含 Markdown 粗體標記")
        category = False
        children = 0
        for line in content.splitlines():
            if not line.strip():
                raise MMISClientError(f"AI 分析的「{field}」含空白條列")
            if field == "改善對策" and line.startswith("  * "):
                if not category or not line[4:].strip():
                    raise MMISClientError("改善對策子項目縮排或分類無效")
                children += 1
            elif line.startswith("* ") and line[2:].strip():
                if field == "改善對策":
                    if category and children == 0:
                        raise MMISClientError("改善對策分類缺少子項目")
                    title = line[2:].strip()
                    category = title.endswith(("：", ":"))
                    if category and title not in CATEGORIES:
                        raise MMISClientError("改善對策分類名稱無效")
                    children = 0
            else:
                raise MMISClientError(f"AI 分析的「{field}」條列格式無效")
        if field == "改善對策" and category and children == 0:
            raise MMISClientError("改善對策分類缺少子項目")
    return value


def merge_fault_analysis(result: dict[str, Any], generated: dict[str, str]) -> dict[str, Any]:
    """Keep every source field and place the sole analysis object last."""
    merged = copy.deepcopy(result)
    original = merged.pop("故障分析", None)
    if original is None:
        original = {}
    if not isinstance(original, dict):
        raise MMISClientError("MMIS 故障分析欄位格式無效")
    merged["故障分析"] = {**original, **generated}
    return merged


def _request(client: OpenAI, config: OpenAIAnalysisConfig, system: str, user: str) -> str:
    try:
        for attempt in range(3):
            try:
                response = client.responses.create(
                    model=config.model,
                    reasoning={"effort": config.reasoning_effort},
                    max_output_tokens=config.max_output_tokens,
                    store=False,
                    input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    text={"format": {"type": "json_schema", "name": "fault_analysis", "strict": True, "schema": SCHEMA}},
                )
                break
            except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as exc:
                if isinstance(exc, RateLimitError) and getattr(exc, "code", None) == "insufficient_quota":
                    raise MMISClientError("OpenAI API 額度不足") from exc
                retryable = isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError)) or (
                    isinstance(exc, APIStatusError) and exc.status_code >= 500
                )
                if not retryable or attempt == 2:
                    raise
                delay = _retry_delay(exc, attempt)
                if delay > 60:
                    raise MMISClientError("OpenAI 要求稍後重試，請依 Retry-After 再執行") from exc
                time.sleep(delay)
    except AuthenticationError as exc:
        raise MMISClientError("OpenAI API Key 無效") from exc
    except PermissionDeniedError as exc:
        raise MMISClientError("OpenAI 模型存取權限不足") from exc
    except BadRequestError as exc:
        raise MMISClientError("OpenAI 請求被拒絕；請檢查模型 ID 與設定") from exc
    except NotFoundError as exc:
        raise MMISClientError("OpenAI 模型 ID 不存在或目前帳號無法使用") from exc
    except RateLimitError as exc:
        raise MMISClientError("OpenAI 速率限制，重試已達上限") from exc
    except APITimeoutError as exc:
        raise MMISClientError("OpenAI 請求逾時，重試已達上限") from exc
    except APIConnectionError as exc:
        raise MMISClientError("OpenAI 連線失敗，重試已達上限") from exc
    except APIStatusError as exc:
        raise MMISClientError(f"OpenAI 服務錯誤（HTTP {exc.status_code}）") from exc
    if response.status != "completed" or not response.output_text:
        raise MMISClientError("OpenAI 輸出不完整或未提供分析 JSON")
    return response.output_text


def _retry_delay(exc: Exception, attempt: int) -> float:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {})
    retry_after = headers.get("retry-after") if headers else None
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                when = parsedate_to_datetime(retry_after)
                return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError):
                pass
    return float(2 ** attempt)


def analyze_fault_notice(result: dict[str, Any], *, client: OpenAI | None = None) -> dict[str, str]:
    config = OpenAIAnalysisConfig.from_env()
    system = _read_prompt("SystemPrompt.md")
    user = build_user_prompt(result, _read_prompt("UserPrompt.md"))
    client = client or OpenAI(api_key=config.api_key, timeout=config.timeout_seconds, max_retries=0)
    try:
        return validate_analysis(_request(client, config, system, user))
    except MMISClientError as exc:
        if not str(exc).startswith("AI 分析") and not str(exc).startswith("改善對策"):
            raise
        # One targeted regeneration; no local edits to the model's conclusions.
        repaired = user + "\n\n上次輸出格式驗證失敗。請重新生成完整三欄 JSON，逐項遵守條列與改善對策縮排規則。"
        try:
            return validate_analysis(_request(client, config, system, repaired))
        except MMISClientError as second:
            raise MMISClientError(f"AI 分析格式驗證失敗：{second}") from second
