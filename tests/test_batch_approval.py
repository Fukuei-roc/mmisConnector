from pathlib import Path

import pytest

from mmis_connector.auth import MMISClientError
from mmis_connector.batch_approval import (
    EXPECTED_CATEGORIES, approve_all_pending, parse_pending_counts,
)


FIXTURE = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-11-16_uto-batch-approve-work-orders"
    r"\dom\2026-11-16T023315-135.html"
)
SANITIZED_FIXTURE = Path(__file__).parent / "fixtures/batch_approval_tabs.html"


def test_batch_approval_counts_from_sanitized_recording() -> None:
    counts = parse_pending_counts(SANITIZED_FIXTURE.read_text(encoding="utf-8"))
    assert tuple(counts) == EXPECTED_CATEGORIES
    assert counts["1A工單"] == 17
    assert counts["臨時檢修工單"] == 2
    assert sum(counts.values()) == 19


def test_recorded_batch_approval_counts() -> None:
    if not FIXTURE.is_file():
        pytest.skip("錄製 DOM 僅保留在本機")
    counts = parse_pending_counts(FIXTURE.read_text(encoding="utf-8"))
    assert tuple(counts) == EXPECTED_CATEGORIES
    assert counts["1A工單"] == 17
    assert counts["臨時檢修工單"] == 2
    assert sum(counts.values()) == 19


def test_missing_category_is_an_error() -> None:
    tabs = "".join(
        f'<li ctype="tab"><a role="tab" title="{name}(0)"></a></li>'
        for name in EXPECTED_CATEGORIES[:-1]
    )
    html = f'<body data-appid="zz_bchappr">{tabs}</body>'
    with pytest.raises(MMISClientError, match="缺少類型: PO採購作業"):
        parse_pending_counts(html)


def test_wrong_app_is_an_error() -> None:
    with pytest.raises(MMISClientError, match="不是批次核簽頁面"):
        parse_pending_counts('<body data-appid="startcntr"></body>')


def _approval_page(counts: dict[str, int], active: str) -> str:
    tabs = "".join(
        f'<li ctype="tab"><a role="tab" title="{name}({counts[name]})" '
        f'aria-expanded="{str(name == active).lower()}"></a></li>'
        for name in EXPECTED_CATEGORIES
    )
    controls = (
        '<a id="table_ttselallrows-ti"></a>'
        '<button id="table_bg_button_EXEWOAPPR-pb"></button>'
    )
    other_tabs = (
        '<li ctype="tab"><a role="tab" title="檢修回報" '
        'aria-expanded="true"></a></li>'
        '<li ctype="tab"><a role="tab" title="重要事項清單" '
        'aria-expanded="true"></a></li>'
    )
    return f'<body data-appid="zz_bchappr">{tabs}{other_tabs}{controls}</body>'


def _dialog(button_id: str, message: str = "") -> str:
    return (
        '<server_response><component compid="msgbox-dialog"><![CDATA['
        f'<span>{message}</span>'
        f'<button ctype="pushbutton" class="pb default" id="{button_id}">'
        '確定</button>]]></component></server_response>'
    )


def test_approval_loops_and_counts_confirmed_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    from mmis_connector import batch_approval

    initial = {name: 0 for name in EXPECTED_CATEGORIES}
    initial["1A工單"] = 16
    initial["定期檢修工單"] = 2
    after_first = dict(initial, **{"1A工單": 2})
    after_second = dict(initial, **{"1A工單": 0})
    after_third = {name: 0 for name in EXPECTED_CATEGORIES}
    pages = iter([
        _approval_page(after_first, "1A工單"),
        _approval_page(after_second, "定期檢修工單"),
        _approval_page(after_third, "定期檢修工單"),
    ])
    batch_sizes = (15, 1, 2)
    sent: list[str] = []

    class FakeSession:
        def refresh_state(self):
            return type("State", (), {"app_id": "zz_bchappr"})(), next(pages)

    class FakeEvents:
        def __init__(self, client):
            pass

        def load_app_with_response(self, **kwargs):
            return object(), _approval_page(initial, "1A工單")

        def post(self, **kwargs):
            assert kwargs["current_focus"] == kwargs["target_id"]
            assert kwargs["xhr_seq"] == len(sent) + 1
            sent.append(kwargs["target_id"])
            step = len(sent) % 4
            if step == 1:
                return '<server_response><component><![CDATA[<button id="table_bg_button_EXEWOAPPR-pb"></button>]]></component></server_response>'
            if step == 2:
                size = batch_sizes[(len(sent) - 1) // 4]
                return _dialog("yes-pb", f"即將核簽{size}筆，核准{size}筆，退回0筆")
            if step == 3:
                return _dialog("ok-pb", "BMXZZ7134I 批次核簽成功")
            return "<server_response/>"

    monkeypatch.setattr(batch_approval, "MaximoEventClient", FakeEvents)
    result = approve_all_pending(FakeSession())
    assert result["1A工單"] == 16
    assert result["定期檢修工單"] == 2
    assert sum(result.values()) == 18
    assert sent == [
        "table_ttselallrows-ti", "table_bg_button_EXEWOAPPR-pb", "yes-pb", "ok-pb"
    ] * 3


def test_approval_stops_if_success_signal_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from mmis_connector import batch_approval

    counts = {name: 0 for name in EXPECTED_CATEGORIES}
    counts["1A工單"] = 1
    page = _approval_page(counts, "1A工單")

    class FakeSession:
        def refresh_state(self):
            return type("State", (), {"app_id": "zz_bchappr"})(), page

    class FakeEvents:
        def __init__(self, client):
            self.calls = 0

        def load_app_with_response(self, **kwargs):
            return object(), page

        def post(self, **kwargs):
            self.calls += 1
            return (
                '<server_response><component><![CDATA[<button id="table_bg_button_EXEWOAPPR-pb"></button>]]></component></server_response>'
                if self.calls == 1 else _dialog("yes-pb", "即將核簽1筆，核准1筆，退回0筆")
                if self.calls == 2 else _dialog("ok-pb", "其他訊息")
            )

    monkeypatch.setattr(batch_approval, "MaximoEventClient", FakeEvents)
    with pytest.raises(MMISClientError, match="未確認本輪批次核簽成功"):
        approve_all_pending(FakeSession())
