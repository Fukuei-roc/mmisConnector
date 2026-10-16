"""Read the three dependent ATP lookup lists through Maximo UI events."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..auth import MMISClientError, MMISSession
from ..events import MaximoEventClient
from ..parser import (
    _parse_maximo_markup,
    parse_atp_fault_checked,
    parse_maximo_page_info,
    parse_maximo_tab_target,
    parse_maximo_table,
    parse_maximo_table_schema,
)
from .reader import FaultNoticeAnalysisReader, normalize_fault_notice


LOOKUPS = (("故障要因", "VALUELIST", "ZZ_FNM_FACTOR"),
           ("故障因子", "ZZ_FNM_ELEMENT", None),
           ("故障項目", "ZZ_FNM_EVENT", None))
LOOKUP_PREFIX = "lookup_page1"
ROW_TARGET = re.compile(r"^lookup_page1_tdrow_\[C:0\]_ttxt-lb\[R:(\d+)\]$")


def _field_controls(markup: str) -> dict[str, tuple[str, str]]:
    """Find the recorded lookup controls by label and lookup metadata."""
    _, soup = _parse_maximo_markup(markup)
    result: dict[str, tuple[str, str]] = {}
    for name, lookup, dsid in LOOKUPS:
        matches = []
        for label in soup.find_all("label", attrs={"for": True}):
            if label.get_text(" ", strip=True).rstrip("：:").strip() != name:
                continue
            field = soup.find("input", id=label["for"])
            if field is None:
                continue
            try:
                info = json.loads(field.get("fldinfo", "{}"))
            except ValueError:
                continue
            if info.get("lookup") != lookup or (dsid and info.get("dsid") != dsid):
                continue
            image_id = field.get("li", "")
            if image_id and soup.find(id=image_id):
                matches.append((str(field["id"]), str(image_id)))
        if len(matches) != 1:
            raise MMISClientError(f"ATP 頁面找不到唯一的{name}查詢控制項")
        result[name] = matches[0]
    return result


def parse_lookup_page(markup: str) -> tuple[list[dict[str, str | None]], Any]:
    """Parse one lookup page; a missing table/count is an error, never an empty list."""
    _, soup = _parse_maximo_markup(markup)
    if soup.find(id=LOOKUP_PREFIX + "-to") is None:
        raise MMISClientError("選項回應缺少 lookup_page1 表格")
    page = parse_maximo_page_info(markup, table_prefix=LOOKUP_PREFIX, context_name="ATP選項")
    if page.total == 0:
        schema = parse_maximo_table_schema(markup, required_headers=set())
        rows = []
    else:
        schema, rows = parse_maximo_table(markup, required_headers=set())
    if schema is None or schema.prefix != LOOKUP_PREFIX or 0 not in schema.headers:
        raise MMISClientError("選項回應的欄位結構異常")
    if len(rows) != (page.end - page.start + 1 if page.total else 0):
        raise MMISClientError("選項回應的列數與分頁統計不一致")
    if page.total > page.end and page.next_page_target is None:
        raise MMISClientError("選項回應缺少下一頁控制項")
    options: list[dict[str, str | None]] = []
    for index, row in enumerate(rows):
        name = row[schema.headers[0]]
        target = f"{LOOKUP_PREFIX}_tdrow_[C:0]_ttxt-lb[R:{index}]"
        if not isinstance(name, str) or not name.strip() or soup.find(id=target) is None:
            raise MMISClientError("選項回應缺少名稱或選取控制項")
        options.append({"code": None, "name": name, "_target": target})
    return options, page


class ATPOptionsExporter:
    def __init__(self, client: MMISSession, *, delay_seconds: float = 0.15) -> None:
        self.client = client
        self.events = MaximoEventClient(client)
        self.delay_seconds = delay_seconds
        self.xhr = 1
        self.controls: dict[str, tuple[str, str]] = {}
        self.errors: list[dict[str, Any]] = []
        self.close_target: str | None = None

    def _post(self, *, focus: str, target: str, value: str = "") -> str:
        if self.client.state is None:
            raise MMISClientError("MMIS session 未建立")
        # Only a lookup, row selection, pagination, or tab click is permitted.
        if not (target in {control[1] for control in self.controls.values()}
                or ROW_TARGET.fullmatch(target)
                or target.startswith(LOOKUP_PREFIX + "-ti")
                or target == self.close_target
                or target.endswith("-tab")):
            raise MMISClientError("禁止的 Maximo event target")
        if value not in ("", "VALUELIST", "ZZ_FNM_ELEMENT", "ZZ_FNM_EVENT"):
            raise MMISClientError("禁止的 Maximo event value")
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        self.xhr += 1
        return self.events.post(state=self.client.state, current_focus=focus,
                                event_type="click", target_id=target,
                                value=value, xhr_seq=self.xhr)

    def _open(self, field: str) -> list[dict[str, str | None]]:
        input_id, image_id = self.controls[field]
        lookup = next(value for name, value, _ in LOOKUPS if name == field)
        response = self._post(focus=input_id, target=image_id, value=lookup)
        options: list[dict[str, str | None]] = []
        expected_total: int | None = None
        while True:
            _, soup = _parse_maximo_markup(response)
            close_buttons = [str(button["id"]) for button in soup.find_all("button", id=True)
                             if button.get_text(" ", strip=True) == "取消"]
            if len(close_buttons) != 1:
                raise MMISClientError("選項清單找不到唯一的取消按鈕")
            self.close_target = close_buttons[0]
            rows, page = parse_lookup_page(response)
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total or page.start != len(options) + 1 and page.total:
                raise MMISClientError("選項分頁不連續或總數改變")
            options.extend(rows)
            if not page.next_page_target:
                if len(options) != expected_total:
                    raise MMISClientError("選項分頁未完整取得")
                break
            response = self._post(focus=page.next_page_target,
                                  target=page.next_page_target)
        self._post(focus=self.close_target, target=self.close_target)
        return options

    def _choose(self, field: str, index: int, expected_name: str) -> None:
        """Reopen and select the exact row, including the correct page."""
        input_id, image_id = self.controls[field]
        lookup = next(value for name, value, _ in LOOKUPS if name == field)
        response = self._post(focus=input_id, target=image_id, value=lookup)
        offset = 0
        while True:
            rows, page = parse_lookup_page(response)
            if index < offset + len(rows):
                selected = rows[index - offset]
                if selected["name"] != expected_name:
                    raise MMISClientError("選項清單在遍歷期間發生變更")
                target = str(selected["_target"])
                self._post(focus=target, target=target)
                return
            offset += len(rows)
            if not page.next_page_target:
                raise MMISClientError("找不到預期的選項列")
            response = self._post(focus=page.next_page_target,
                                  target=page.next_page_target)

    @staticmethod
    def _public(option: dict[str, str | None]) -> dict[str, Any]:
        return {"code": option["code"], "name": option["name"]}

    def run(self, fault_notice: str) -> dict[str, Any]:
        notice = normalize_fault_notice(fault_notice)
        reader = FaultNoticeAnalysisReader(self.client)
        state, detail = reader._load_exact_detail(notice)
        if not parse_atp_fault_checked(detail):
            raise MMISClientError("此故障通報未勾選ATP故障")
        self.xhr = reader.next_xhr_seq - 1
        for title in ("故障分析", "故障分析-ATP"):
            tab = parse_maximo_tab_target(detail, title=title)
            detail = self._post(focus=tab, target=tab)
        self.controls = _field_controls(detail)
        causes = self._open("故障要因")
        tree = []
        for cause_index, cause in enumerate(causes):
            cause_node = {**self._public(cause), "factors": []}
            tree.append(cause_node)
            try:
                self._choose("故障要因", cause_index, str(cause["name"]))
                factors = self._open("故障因子")
                for factor_index, factor in enumerate(factors):
                    factor_node = {**self._public(factor), "items": []}
                    cause_node["factors"].append(factor_node)
                    try:
                        self._choose("故障因子", factor_index, str(factor["name"]))
                        items = self._open("故障項目")
                        factor_node["items"] = [self._public(item) for item in items]
                    except MMISClientError as exc:
                        factor_node["items"] = None
                        self.errors.append({"path": [cause["name"], factor["name"]], "reason": str(exc)})
            except MMISClientError as exc:
                cause_node["factors"] = None
                self.errors.append({"path": [cause["name"]], "reason": str(exc)})
        factors_count = sum(len(c["factors"] or []) for c in tree)
        items_count = sum(len(f["items"] or []) for c in tree for f in (c["factors"] or []))
        combinations = sum(len(f["items"]) or 1 for c in tree for f in (c["factors"] or []) if f["items"] is not None)
        combinations += sum(c["factors"] == [] for c in tree)
        return {
            "schema_version": "1.0", "source": "MMIS", "module": "故障通報管理",
            "tab": "故障分析-ATP", "generated_at": datetime.now(timezone.utc).isoformat(),
            "traversal_status": "partial" if self.errors else "completed",
            "statistics": {"causes": len(tree), "factors": factors_count,
                           "items": items_count, "valid_combinations": combinations},
            "fault_causes": tree, "errors": self.errors,
        }


def write_export(result: dict[str, Any], destination: Path) -> Path:
    """Atomically publish a complete result; keep partial runs separately."""
    target = destination if result["traversal_status"] == "completed" else destination.with_name(destination.stem + ".partial.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent,
                                         prefix=".atp-options-", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return target
