from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tools.mmis_development import (
    query_daily_inspection_work_order_by_number as detail_tool,
)
from tools.mmis_development import (
    query_daily_inspection_work_order_by_number_and_link_fault_notice as link_tool,
)
from tools.mmis_development import (
    query_daily_inspection_work_orders_by_vehicle_and_date as work_order_tool,
)
from tools.mmis_development import (
    query_unprocessed_fault_notices as unprocessed_tool,
)
from tools.mmis_development import (
    query_unclosed_fault_notices as unclosed_tool,
)


@pytest.mark.parametrize(
    ("tool", "invalid_args"),
    [
        (unprocessed_tool, ["unexpected"]),
        (unclosed_tool, ["unexpected"]),
        (work_order_tool, ["703"]),
        (detail_tool, []),
        (link_tool, ["115-1A-71002"]),
    ],
)
def test_tool_rejects_invalid_arguments_before_loading_config(
    tool, invalid_args, monkeypatch, capsys
) -> None:
    def unexpected_config_load():
        raise AssertionError("config should not load for invalid arguments")

    monkeypatch.setattr(tool.MMISConfig, "from_env", unexpected_config_load)

    exit_code = tool.main(invalid_args)
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["error"] == "MMISClientError"
    assert result["message"].startswith("用法: python -m tools.mmis_development.")


def _patch_client(tool, monkeypatch):
    config = object()
    client = SimpleNamespace(login_calls=0)

    def login():
        client.login_calls += 1

    client.login = login
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        tool,
        "MMISSession",
        lambda actual_config: client if actual_config is config else None,
    )
    return client


def test_unprocessed_tool_invokes_formal_query(monkeypatch, capsys) -> None:
    client = _patch_client(unprocessed_tool, monkeypatch)
    expected = {"success": True, "count": 0, "records": []}

    class FakeQuery:
        def __init__(self, actual_client):
            assert actual_client is client

        def run(self):
            return expected

    monkeypatch.setattr(unprocessed_tool, "UnprocessedFaultNoticeQuery", FakeQuery)

    assert unprocessed_tool.main([]) == 0
    assert client.login_calls == 1
    assert json.loads(capsys.readouterr().out) == expected


def test_unclosed_tool_invokes_formal_query(monkeypatch, capsys) -> None:
    client = _patch_client(unclosed_tool, monkeypatch)
    expected = {
        "success": True,
        "query_name": "故障通報未結案清單",
        "filters": {"配屬段別名稱": "新竹機務段", "事故等級": "A,B"},
        "count": 0,
        "records": [],
    }

    class FakeQuery:
        def __init__(self, actual_client):
            assert actual_client is client

        def run(self):
            return expected

    monkeypatch.setattr(unclosed_tool, "UnclosedFaultNoticeQuery", FakeQuery)

    assert unclosed_tool.main([]) == 0
    assert client.login_calls == 1
    assert json.loads(capsys.readouterr().out) == expected


def test_work_order_tool_forwards_vehicle_and_date(monkeypatch, capsys) -> None:
    client = _patch_client(work_order_tool, monkeypatch)
    expected = {"success": True, "count": 0, "records": []}
    received = []

    class FakeQuery:
        def __init__(self, actual_client):
            assert actual_client is client

        def run(self, *args):
            received.extend(args)
            return expected

    monkeypatch.setattr(work_order_tool, "DailyInspectionWorkOrderQuery", FakeQuery)

    assert work_order_tool.main(["703", ">2026/09/22"]) == 0
    assert received == ["703", ">2026/09/22"]
    assert json.loads(capsys.readouterr().out) == expected


def test_detail_tool_forwards_work_order(monkeypatch, capsys) -> None:
    client = _patch_client(detail_tool, monkeypatch)
    expected = {"success": True, "count": 0, "records": []}
    received = []

    class FakeReader:
        def __init__(self, actual_client):
            assert actual_client is client

        def run(self, work_order):
            received.append(work_order)
            return expected

    monkeypatch.setattr(
        detail_tool, "DailyInspectionWorkOrderDetailReader", FakeReader
    )

    assert detail_tool.main(["115-1A-70048"]) == 0
    assert received == ["115-1A-70048"]
    assert json.loads(capsys.readouterr().out) == expected


def test_link_tool_forwards_work_order_and_fault_notice(
    monkeypatch, capsys
) -> None:
    client = _patch_client(link_tool, monkeypatch)
    expected = {"success": True, "linked": True, "returned_to_list": True}
    received = []

    class FakeLinker:
        def __init__(self, actual_client):
            assert actual_client is client

        def run(self, *args):
            received.extend(args)
            return expected

    monkeypatch.setattr(
        link_tool, "DailyInspectionWorkOrderFaultNoticeLinker", FakeLinker
    )

    assert link_tool.main(["115-1A-71002", "1150923-36"]) == 0
    assert received == ["115-1A-71002", "1150923-36"]
    assert json.loads(capsys.readouterr().out) == expected
