from __future__ import annotations

from ..auth import MMISClientError, MMISSession
from ..parser import (
    parse_labeled_textarea_targets,
    parse_labeled_textareas,
    parse_maximo_tab_target,
)
from .reader import FaultNoticeAnalysisReader, normalize_fault_notice


WRITE_FIELDS = ("故障原因", "處理情形", "改善對策")
SAVE_TARGET = "toolactions_SAVE-tbb"
SAVE_MESSAGE = "BMXAA4205I"


class FaultNoticeAnalysisWriter(FaultNoticeAnalysisReader):
    """Write and verify three analysis fields on one exact MMIS notice."""

    def __init__(self, client: MMISSession) -> None:
        super().__init__(client)

    def run(self, notice_number: str, values: dict[str, str]) -> None:
        notice = normalize_fault_notice(notice_number)
        if set(values) != set(WRITE_FIELDS) or any(
            not isinstance(values[field], str) or not values[field].strip()
            for field in WRITE_FIELDS
        ):
            raise MMISClientError("故障分析三欄必須是非空文字")

        state, detail_response = self._load_exact_detail(notice)
        tab = parse_maximo_tab_target(detail_response, title="故障分析")
        response = self._post_event(
            state=self.client.state or state,
            current_focus=tab,
            event_type="click",
            target_id=tab,
            value="",
            xhr_seq=self.next_xhr_seq,
        )
        targets = parse_labeled_textarea_targets(response, field_names=WRITE_FIELDS)
        current = parse_labeled_textareas(response, field_names=WRITE_FIELDS)
        final_values = {
            field: current[field] if current[field].strip() else values[field]
            for field in WRITE_FIELDS
        }
        if current == final_values:
            return

        try:
            for offset, field in enumerate(WRITE_FIELDS[:-1], start=1):
                self.events.post(
                    state=self.client.state or state,
                    current_focus=targets[field],
                    event_type="setvalue",
                    target_id=targets[field],
                    value=final_values[field],
                    xhr_seq=self.next_xhr_seq + offset,
                )
            last = WRITE_FIELDS[-1]
            saved = self.events.post_events(
                state=self.client.state or state,
                current_focus=targets[last],
                events=[
                    ("setvalue", targets[last], final_values[last]),
                    ("click", SAVE_TARGET, ""),
                ],
                xhr_seq=self.next_xhr_seq + len(WRITE_FIELDS),
            )
        except Exception as exc:
            raise MMISClientError("故障分析儲存結果不明，未自動重送") from exc
        if SAVE_MESSAGE not in saved:
            raise MMISClientError("故障分析儲存結果不明，未收到 MMIS 儲存確認")

        confirmation = FaultNoticeAnalysisReader(self.client).run(notice)
        if any(
            confirmation["analysis"].get(field) != final_values[field]
            for field in WRITE_FIELDS
        ):
            raise MMISClientError("故障分析儲存後三欄內容不符")
