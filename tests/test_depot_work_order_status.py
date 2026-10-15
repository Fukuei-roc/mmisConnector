from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from tools.mmis_development import query_fault_notice_full_detail as tool


@pytest.mark.parametrize(("statuses", "closed", "pending"), [
    (["工單結案"], True, False),
    (["工單結案", "工單結案"], True, False),
    (["工單結案", "簽核中"], False, True),
    (["簽核中", "簽核中"], False, True),
    (["工單結案", "執行中"], False, False),
    (["執行中", "簽核中"], False, True),
    (["工單結案", "執行中", "簽核中"], False, True),
    (["執行中", "執行中"], False, False),
    ([], False, False),
    ([None, "工單結案"], False, False),
    ([None, "簽核中"], False, True),
    (["", "工單結案"], False, False),
    (["已派工", "退回", "取消", "其他系統狀態"], False, False),
])
def test_evaluate_depot_work_order_status(statuses, closed, pending):
    orders = [{"工作單狀態": status, "狀態": "處理完成"} for status in statuses]
    before = copy.deepcopy(orders)

    result = tool.evaluate_depot_work_order_status(orders)

    assert result == {
        "All Depot Maintenance Work Orders Closed": closed,
        "Depot Maintenance Work Orders Pending Approval": pending,
    }
    assert all(type(value) is bool for value in result.values())
    assert orders == before


def test_missing_work_order_status_is_not_closed_or_pending():
    orders = [{"狀態": "工單結案"}, {"工作單狀態": "簽核中", "狀態": "處理完成"}]
    assert tool.evaluate_depot_work_order_status(orders) == {
        "All Depot Maintenance Work Orders Closed": False,
        "Depot Maintenance Work Orders Pending Approval": True,
    }


def test_execute_reuses_original_orders_and_preserves_output(monkeypatch):
    orders = [
        {"工作單": "115-1A-73469", "工作單狀態": "工單結案", "狀態": "併單"},
        {"工作單": "115-C1-41264", "工作單狀態": "工單結案", "狀態": "處理完成"},
    ]
    source = {
        "通報號": "1151005-29",
        "段修工單": orders,
        "CA查修工單": [],
        "故障分析": {"故障原因": "甲", "處理情形": "乙", "改善對策": "丙"},
        "ATP故障分析": None,
    }
    original = copy.deepcopy(source)
    materials = {"臨時檢修工單": [], "日檢工單": [], "定期檢修工單": []}
    calls = []
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", lambda _: SimpleNamespace(login=lambda: calls.append("login")))
    monkeypatch.setattr(tool.FaultNoticeFullDetailReader, "run", lambda self, _: source)

    def collect(client, work_orders):
        assert work_orders is orders
        calls.append("materials")
        return materials

    monkeypatch.setattr(tool, "collect_analysis_materials", collect)

    result = tool.execute(["1151005-29"])

    assert calls == ["login", "materials"]
    assert list(result)[-4:] == [
        "Fault Analysis Completed",
        "All Depot Maintenance Work Orders Closed",
        "Depot Maintenance Work Orders Pending Approval",
        "故障分析素材",
    ]
    assert result["Fault Analysis Completed"] is True
    assert result["All Depot Maintenance Work Orders Closed"] is True
    assert result["Depot Maintenance Work Orders Pending Approval"] is False
    assert result["故障分析素材"] is materials
    assert {key: result[key] for key in original} == original
