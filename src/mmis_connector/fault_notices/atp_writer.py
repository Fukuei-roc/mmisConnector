from __future__ import annotations

from ..auth import MMISClientError, MMISSession
from ..parser import (
    parse_atp_fault_checked,
    parse_labeled_inputs,
    parse_labeled_input_targets,
    parse_maximo_tab_target,
)
from .analysis_writer import SAVE_MESSAGE, SAVE_TARGET
from .atp_reader import ATP_ANALYSIS_FIELDS, FaultNoticeATPAnalysisReader
from .reader import normalize_fault_notice


class ATPAnalysisAlreadyFilled(MMISClientError):
    """The recorded all-empty ATP write path does not apply to this notice."""


class FaultNoticeATPAnalysisWriter(FaultNoticeATPAnalysisReader):
    def __init__(self, client: MMISSession) -> None:
        super().__init__(client)

    def run(self, notice_number: str, values: dict[str, str]) -> None:
        notice = normalize_fault_notice(notice_number)
        if set(values) != set(ATP_ANALYSIS_FIELDS) or any(
            not isinstance(values[field], str) or not values[field].strip()
            for field in ATP_ANALYSIS_FIELDS
        ):
            raise MMISClientError("ATP 故障分析三欄必須是非空文字")

        state, detail = self._load_exact_detail(notice)
        if not parse_atp_fault_checked(detail):
            raise MMISClientError("此故障通報未勾選ATP故障")
        for offset, title in enumerate(("故障分析", "故障分析-ATP")):
            tab = parse_maximo_tab_target(detail, title=title)
            detail = self._post_event(
                state=self.client.state or state,
                current_focus=tab,
                event_type="click",
                target_id=tab,
                value="",
                xhr_seq=self.next_xhr_seq + offset,
            )

        current = parse_labeled_inputs(
            detail, field_names=ATP_ANALYSIS_FIELDS, context_name="ATP故障分析"
        )
        if any(current[field].strip() for field in ATP_ANALYSIS_FIELDS):
            raise ATPAnalysisAlreadyFilled("ATP 故障分析已有文字，未覆蓋既有分類")
        targets = parse_labeled_input_targets(
            detail, field_names=ATP_ANALYSIS_FIELDS, context_name="ATP故障分析"
        )
        try:
            for offset, field in enumerate(ATP_ANALYSIS_FIELDS[:-1], start=2):
                self.events.post(
                    state=self.client.state or state,
                    current_focus=targets[ATP_ANALYSIS_FIELDS[offset - 1]],
                    event_type="setvalue",
                    target_id=targets[field],
                    value=values[field],
                    xhr_seq=self.next_xhr_seq + offset,
                )
            last = ATP_ANALYSIS_FIELDS[-1]
            saved = self.events.post_events(
                state=self.client.state or state,
                current_focus=targets[last],
                events=[
                    ("setvalue", targets[last], values[last]),
                    ("click", SAVE_TARGET, ""),
                ],
                xhr_seq=self.next_xhr_seq + len(ATP_ANALYSIS_FIELDS) + 1,
            )
        except Exception as exc:
            raise MMISClientError("ATP 故障分析儲存結果不明，未自動重送") from exc
        if SAVE_MESSAGE not in saved:
            raise MMISClientError("ATP 故障分析儲存結果不明，未收到 MMIS 儲存確認")

        confirmation = FaultNoticeATPAnalysisReader(self.client).run(notice)
        if confirmation["analysis"] != values:
            raise MMISClientError("ATP 故障分析儲存後三欄內容不符")
