from __future__ import annotations

from unittest.mock import Mock

import pytest

from mmis_connector.auth import MMISClientError
from mmis_connector.daily_inspection.cancel import (
    DailyInspectionWorkOrderCanceller,
    _dialog_controls,
)


def detail(status: str) -> str:
    fields = {"工作單": "115-1A-81454", "車組/車號": "717", "檢修日期": "2026/11/04",
              "車次": "1", "工作單狀態": status, "開單人姓名": "A", "開單日期": "2026/11/04"}
    labels = "".join(f'<label for="f{i}">{name}:</label><input id="f{i}" value="{value}">'
                     for i, (name, value) in enumerate(fields.items()))
    return labels + '<input aria-label="檢修段 說明" value="新竹機務段">' \
        '<li id="toolactions_ZZ_WOCAN-tbb"><a title="工單取消"></a></li>'


def test_non_unassigned_status_never_sends_cancel_event() -> None:
    client = Mock()
    client.state = Mock()
    canceller = DailyInspectionWorkOrderCanceller(client)
    canceller.events = Mock()
    canceller.reader.open_detail = Mock(return_value=("115-1A-81454", detail("執行中已派工")))

    with pytest.raises(MMISClientError, match="非執行中未派工工單不可刪除"):
        canceller.run("115-1A-81454")

    canceller.events.post.assert_not_called()
    canceller.events.post_events.assert_not_called()


def test_cancel_uses_recorded_sequence_and_verifies_status() -> None:
    client = Mock()
    client.state = Mock()
    canceller = DailyInspectionWorkOrderCanceller(client)
    canceller.events = Mock()
    canceller.reader.open_detail = Mock(side_effect=[
        ("115-1A-81454", detail("執行中未派工")),
        ("115-1A-81454", detail("工單取消")),
    ])
    canceller.events.post.side_effect = [
        '<div id="ZZ_WOCAN-dialog_inner"><textarea id="reason"></textarea><button id="ok">確定</button></div>',
        "",
    ]
    canceller.events.post_events.return_value = (
        '<div id="msgbox-dialog_inner"><button id="yes">是</button></div>'
    )

    result = canceller.run("115-1A-81454")

    assert result["工作單狀態"] == "工單取消"
    assert canceller.events.post_events.call_args.kwargs["events"] == [
        ("setvalue", "reason", "重複開單"), ("click", "ok", "")
    ]
    assert canceller.events.post.call_args.kwargs["target_id"] == "yes"


def test_missing_confirmation_fails_closed() -> None:
    with pytest.raises(MMISClientError, match="找不到唯一的確認按鈕"):
        _dialog_controls('<div id="msgbox-dialog_inner"></div>', "msgbox")
