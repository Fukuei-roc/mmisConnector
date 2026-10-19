from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
import requests

from mmis_connector.auth import MMISClientError
from mmis_connector.fault_notices.analysis_materials import (
    classify_work_order, collect_analysis_materials, extract_fields,
    is_transient_network_error, query_with_retry,
)
from tools.mmis_development import query_fault_notice_full_detail as tool


@pytest.mark.parametrize(("number", "kind"), [
    ("115-1A-70151", "日檢工單"),
    ("115-C1-35820", "臨時檢修工單"),
    ("115-C2-35988", "臨時檢修工單"),
    ("115-C3-12345", "臨時檢修工單"),
    ("115-2A-69254-001", "定期檢修工單"),
    ("115-3A-65245", "定期檢修工單"),
])
def test_classify_work_order(number: str, kind: str) -> None:
    assert classify_work_order(number) == kind


def test_extract_only_requested_fields_and_preserve_nested_data() -> None:
    nested = {"count": 2, "records": [{"備註": "第一行\n第二行", "額外欄位": "保留"}, {"x": 2}]}
    for kind in ("臨時檢修工單", "日檢工單", "定期檢修工單"):
        source = {
            "success": True, "query_name": "ignored", "work_order": "legacy-value",
            "工作單": "115-1A-1", "車組/車號": "EMA815", "故障現象": "現象",
            "原因說明": "原因", "備註": "備註", "維修程序概況": nested,
            "檢修記錄": nested, "重要事項紀錄": nested,
            "維修情形": "甲\n乙", "維修情形(詳述)": "丙\n丁",
        }
        result = extract_fields(kind, source, "fallback")
        assert "success" not in result and "query_name" not in result
        assert "work_order" not in result
        assert result["工作單"] == source["工作單"]
        assert all(result[field] == nested for field in result if field in ("維修程序概況", "檢修記錄", "重要事項紀錄"))
        if kind == "定期檢修工單":
            assert result["維修情形(詳述)"] == "丙\n丁"
        nested_copy = result.get("維修程序概況") or result.get("檢修記錄")
        nested_copy["records"][0]["額外欄位"] = "changed"
        assert nested["records"][0]["額外欄位"] == "保留"
    assert extract_fields("日檢工單", {"success": True}, "115-1A-1") == {
        "工作單": "115-1A-1", "車組/車號": None,
        "檢修記錄": {"count": 0, "records": []},
        "重要事項紀錄": {"count": 0, "records": []},
    }


@pytest.mark.parametrize(("errors", "expected_calls", "waits"), [
    ([requests.ConnectionError("down")], 2, []),
    ([MMISClientError("MMIS 網路請求失敗: ConnectionError"),
      {"success": False, "error": "MMISClientError", "message": "MMIS 網路請求失敗: TimeoutError"}], 3, [1]),
])
def test_retry_then_success(monkeypatch: pytest.MonkeyPatch, errors: list[object], expected_calls: int, waits: list[int]) -> None:
    calls = 0
    slept: list[int] = []
    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.time.sleep", slept.append)

    def query(_: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls <= len(errors):
            error = errors[calls - 1]
            if isinstance(error, Exception):
                raise error
            return error
        return {"success": True, "工作單": "115-1A-1"}

    assert query_with_retry(query, "115-1A-1")["success"] is True
    assert calls == expected_calls and slept == waits


def test_retry_exhaustion_and_non_network(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[int] = []
    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.time.sleep", slept.append)
    calls = 0

    def network(_: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        raise MMISClientError("MMIS 網路請求失敗: ConnectionError")

    with pytest.raises(MMISClientError, match="ConnectionError"):
        query_with_retry(network, "115-C1-1")
    assert calls == 3 and slept == [1]
    calls = 0

    def missing(_: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"success": False, "error": "MMISClientError", "message": "找不到工作單"}

    with pytest.raises(MMISClientError, match="找不到工作單"):
        query_with_retry(missing, "115-C1-1")
    assert calls == 1
    assert is_transient_network_error(MMISClientError("MMIS 回傳非預期 HTTP 狀態: 503"))
    assert not is_transient_network_error(MMISClientError("MMIS 回傳非預期 HTTP 狀態: 403"))


def test_collection_preserves_order_duplicates_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    def temporary(self: object, number: str) -> dict[str, object]:
        calls.append(number)
        if number.endswith("2"):
            raise MMISClientError("找不到工作單")
        return {"success": True, "工作單": number, "維修程序概況": {"count": 1, "records": [{"raw": "a\nb"}]}}

    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.TemporaryRepairProcedureReader.run", temporary)
    rows = [
        {"工作單": "115-C1-1", "工單級別": "1A"},
        {"工作單": "115-C2-2"},
        {"工作單": "115-C3-3"},
        {"工作單": "115-C1-1"},
        {"工作單": "bad"},
    ]
    result = collect_analysis_materials(SimpleNamespace(), rows)
    assert list(result) == ["臨時檢修工單", "日檢工單", "定期檢修工單"]
    assert calls == ["115-C1-1", "115-C2-2", "115-C3-3"]
    assert [x["工作單"] for x in result["臨時檢修工單"]] == ["115-C1-1", "115-C2-2", "115-C3-3", "115-C1-1"]
    assert all("work_order" not in x for x in result["臨時檢修工單"])
    assert result["臨時檢修工單"][1]["查詢狀態"] == "失敗"
    assert result["臨時檢修工單"][1]["錯誤訊息"] == "找不到工作單"
    assert result["臨時檢修工單"][0]["維修程序概況"]["records"][0]["raw"] == "a\nb"
    assert result["日檢工單"] == result["定期檢修工單"] == []
    assert collect_analysis_materials(SimpleNamespace(), []) == {kind: [] for kind in result}


def test_collection_dispatches_all_three_readers_with_same_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object, str]] = []
    client = SimpleNamespace()

    def fake(kind: str):
        def run(self: object, number: str) -> dict[str, object]:
            calls.append((kind, self.client, number))
            return {"success": True, "工作單": number}
        return run

    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.TemporaryRepairProcedureReader.run", fake("臨時檢修工單"))
    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.DailyInspectionInspectionRecordReader.run", fake("日檢工單"))
    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.PeriodicInspectionWorkOrderDetailReader.run", fake("定期檢修工單"))
    result = collect_analysis_materials(client, [
        {"工作單": "115-C2-1"}, {"工作單": "115-1A-2"}, {"工作單": "115-3A-3"},
    ])
    assert calls == [
        ("臨時檢修工單", client, "115-C2-1"),
        ("日檢工單", client, "115-1A-2"),
        ("定期檢修工單", client, "115-3A-3"),
    ]
    assert [len(rows) for rows in result.values()] == [1, 1, 1]


def test_cli_appends_materials_without_mutating_original(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = {"通報號": "1150910-14", "是ATP故障": False, "段修工單": [{"工作單": "115-C1-1"}], "故障分析": {"故障原因": "甲", "處理情形": "乙", "改善對策": "丙"}}
    original = copy.deepcopy(source)
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: SimpleNamespace())
    monkeypatch.setattr(tool, "MMISSession", lambda _: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool.FaultNoticeFullDetailReader, "run", lambda self, _: source)
    monkeypatch.setattr(tool, "collect_analysis_materials", lambda client, rows: {"臨時檢修工單": [], "日檢工單": [], "定期檢修工單": []})
    assert tool.main(["1150910-14"]) == 0
    output = capsys.readouterr()
    parsed = json.loads(output.out)
    assert output.err == ""
    assert list(parsed)[-1:] == ["故障分析素材"]
    assert list(parsed)[list(parsed).index("是ATP故障") + 1] == "結案狀態檢查"
    assert list(parsed["結案狀態檢查"]) == [
        "Sufficient Data for Fault Analysis",
        "Fault Analysis Completed",
        "All Depot Maintenance Work Orders Closed",
        "Depot Maintenance Work Orders Pending Approval",
        "CA Repair Work Orders Not Closed",
        "ATP Fault Analysis Incomplete",
    ]
    assert parsed["結案狀態檢查"] == {
        "Sufficient Data for Fault Analysis": None,
        "Fault Analysis Completed": True,
        "All Depot Maintenance Work Orders Closed": False,
        "Depot Maintenance Work Orders Pending Approval": False,
        "CA Repair Work Orders Not Closed": False,
        "ATP Fault Analysis Incomplete": False,
    }
    assert not set(parsed["結案狀態檢查"]) & set(parsed)
    assert {key: parsed[key] for key in original} == original


def test_cli_materials_use_work_order_label_for_temporary_repairs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    source = {
        "通報號": "1150910-14",
        "是ATP故障": False,
        "段修工單": [{"工作單": number} for number in (
            "115-C1-35820", "115-C2-35988", "115-C3-12345", "115-1A-70151", "115-2A-69254-001",
        )],
        "CA查修工單": [{"工作單": "115-CA-40035"}],
        "故障分析": {"故障原因": "甲", "處理情形": "乙", "改善對策": "丙"},
    }
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: SimpleNamespace())
    monkeypatch.setattr(tool, "MMISSession", lambda _: SimpleNamespace(login=lambda: None))
    monkeypatch.setattr(tool.FaultNoticeFullDetailReader, "run", lambda self, _: source)

    def temporary(self: object, number: str) -> dict[str, object]:
        if "-C2-" in number:
            raise MMISClientError("找不到工作單")
        return {"success": True, "工作單": number, "車組/車號": "EMU935"}

    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.TemporaryRepairProcedureReader.run", temporary)
    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.DailyInspectionInspectionRecordReader.run", lambda self, number: {"success": True, "工作單": number})
    monkeypatch.setattr("mmis_connector.fault_notices.analysis_materials.PeriodicInspectionWorkOrderDetailReader.run", lambda self, number: {"success": True, "工作單": number})

    assert tool.main(["1150910-14"]) == 0
    output = capsys.readouterr()
    parsed = json.loads(output.out)
    materials = parsed["故障分析素材"]
    temporary_rows = materials["臨時檢修工單"]
    assert [row["工作單"] for row in temporary_rows] == ["115-C1-35820", "115-C2-35988", "115-C3-12345"]
    assert all("work_order" not in row for row in temporary_rows)
    assert temporary_rows[1] == {"工作單": "115-C2-35988", "查詢狀態": "失敗", "錯誤訊息": "找不到工作單"}
    assert [row["工作單"] for row in materials["日檢工單"]] == ["115-1A-70151"]
    assert [row["工作單"] for row in materials["定期檢修工單"]] == ["115-2A-69254-001"]
    assert {key: parsed[key] for key in source} == source
