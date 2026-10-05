from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.parser import _parse_maximo_markup
from mmis_connector.temporary_repair.reader import (
    TemporaryRepairProcedureReader,
    _note_record,
    _note_table_summary,
)
from tools.mmis_development import (
    query_temporary_repair_work_order_maintenance_procedure_summary as tool,
)


RECORDING = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-05_query-temporary-repair-work-order-maintenance-procedure-summary"
    r"\raw.har"
)


def test_recorded_flow_reads_two_rows_and_only_requested_fields(monkeypatch) -> None:
    if not RECORDING.exists():
        pytest.skip("錄製 HAR 不在本機")
    entries = json.loads(RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    responses = iter(entries[index]["response"]["content"]["text"] for index in (341, 345, 346, 348, 349, 353, 363))
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    client = SimpleNamespace(state=state)
    reader = TemporaryRepairProcedureReader(client)
    calls = []

    def load_app(**kwargs):
        assert kwargs["app_value"] == "ZZ_CMWO"
        return state

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "load_app", load_app)
    monkeypatch.setattr(reader.events, "post", post)

    result = reader.run(" 115-C2-41266 ")

    assert result["success"] is True
    assert result["work_order"] == "115-C2-41266"
    assert result["count"] == 2
    assert [row["車組/車號"] for row in result["records"]] == ["ED813", "ED813"]
    assert [row["故障類別"] for row in result["records"]] == ["911", "111"]
    assert [row["材料編號(PA)"] for row in result["records"]] == ["1780011124", "120338212D"]
    assert [row["更換數量"] for row in result["records"]] == ["1.00", "1.00"]
    assert result["records"][0]["故障現象"] == "其它問題：Batk2不動作"
    assert result["records"][1]["故障現象"] == "集電舟碳刷撞損"
    assert all(len(row) == 9 and "故障類別說明" in row for row in result["records"])
    assert [(call["event_type"], call["value"]) for call in calls] == [
        ("click", ""), ("click", "useAllRecsQuery_OPTION"),
        ("setvalue", "115-C2-41266"), ("setvalue", "C1,C2,C3"),
        ("filterrows", ""), ("click", ""), ("click", ""),
    ]


def test_note_table_must_have_replacement_quantity_header() -> None:
    html = '<table summary="紀事(備註)清單(1)"><span id="a_ttrow_[C:8]_ttitle-lb">數量</span></table>'
    with pytest.raises(MMISClientError, match="更換數量"):
        _note_table_summary(html)


def test_c1_note_uses_row_vehicle_and_category_description() -> None:
    fields = {
        "故障類別": "351",
        "故障類別說明": "軔機控制單元",
        "故障現象": "其它問題",
        "故障原因": "不良",
        "處置措施": "更換",
        "維修程序": "第一行\n第二行",
        "材料編號(PA)": "1221972541",
        "更換數量": "1.00",
        "車組/車號": "EMA815",
    }
    record = _note_record(fields, vehicle="ED813", description_header="故障類別說明")
    assert record == fields


def test_c2_note_uses_detail_vehicle_and_type_description() -> None:
    fields = {
        "故障類別": "911",
        "故障類型說明": "充電器",
        "故障現象": "其它問題",
        "故障原因": "不良",
        "處置措施": "更換",
        "維修程序": "更換後正常",
        "材料編號(PA)": "1780011124",
        "更換數量": "1.00",
    }
    record = _note_record(fields, vehicle="ED813", description_header="故障類型說明")
    assert record["車組/車號"] == "ED813"
    assert record["故障類別說明"] == "充電器"
    assert "故障類型說明" not in record
    assert len(record) == 9


def test_empty_recorded_note_table_returns_empty_array(monkeypatch) -> None:
    if not RECORDING.exists():
        pytest.skip("錄製 HAR 不在本機")
    entries = json.loads(RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    _, soup = _parse_maximo_markup(entries[363]["response"]["content"]["text"])
    prefix = "me0c66d4a"
    for row in soup.find_all(id=lambda value: bool(value) and value.startswith(f"{prefix}_tbod_tdrow-tr")):
        row.decompose()
    count = soup.find(id=f"{prefix}-lb3")
    assert count is not None
    count.string = "0 - 0/0"
    responses = iter(
        [entries[index]["response"]["content"]["text"] for index in (341, 345, 346, 348, 349, 353)]
        + [str(soup)]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(reader.events, "load_app", lambda **kwargs: state)
    monkeypatch.setattr(reader.events, "post", lambda **kwargs: next(responses))

    result = reader.run("115-C2-41266")

    assert result["count"] == 0
    assert result["records"] == []


def test_other_problem_on_unselected_row_opens_that_rows_detail(monkeypatch) -> None:
    if not RECORDING.exists():
        pytest.skip("錄製 HAR 不在本機")
    entries = json.loads(RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    _, soup = _parse_maximo_markup(entries[363]["response"]["content"]["text"])
    input_node = soup.find(id="me0c66d4a_tdrow_[C:3]_txt-tb[R:1]")
    assert input_node is not None
    input_node["value"] = "其它問題"
    selected_detail = (
        '<component id="me0c66d4a_tbod_tdrow-tr[R:1]_holder">'
        "<script>row.setAttribute('currentrow', 'true');</script></component>"
        '<component><label for="extra-ta">其它故障現象:</label>'
        '<textarea id="extra-ta">第二列補充</textarea></component>'
    )
    responses = iter(
        [entries[index]["response"]["content"]["text"] for index in (341, 345, 346, 348, 349, 353)]
        + [str(soup), selected_detail]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    calls = []
    monkeypatch.setattr(reader.events, "load_app", lambda **kwargs: state)

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "post", post)

    result = reader.run("115-C2-41266")

    assert result["records"][0]["故障現象"] == "其它問題：Batk2不動作"
    assert result["records"][1]["故障現象"] == "其它問題：第二列補充"
    assert calls[-1]["target_id"] == "me0c66d4a_tdrow_[C:0]_tgdet-ti[R:1]"
    assert calls[-1]["xhr_seq"] == 8


def test_row_selection_without_textarea_update_reuses_rendered_value(monkeypatch) -> None:
    if not RECORDING.exists():
        pytest.skip("錄製 HAR 不在本機")
    entries = json.loads(RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    _, soup = _parse_maximo_markup(entries[363]["response"]["content"]["text"])
    input_node = soup.find(id="me0c66d4a_tdrow_[C:3]_txt-tb[R:1]")
    assert input_node is not None
    input_node["value"] = "其它問題"
    unchanged_detail = (
        '<component id="me0c66d4a_tbod_tdrow-tr[R:1]_holder">'
        "<script>row.setAttribute('currentrow', 'true');</script></component>"
    )
    responses = iter(
        [entries[index]["response"]["content"]["text"] for index in (341, 345, 346, 348, 349, 353)]
        + [str(soup), unchanged_detail]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(reader.events, "load_app", lambda **kwargs: state)
    monkeypatch.setattr(reader.events, "post", lambda **kwargs: next(responses))

    result = reader.run("115-C2-41266")

    assert [row["故障現象"] for row in result["records"]] == [
        "其它問題：Batk2不動作",
        "其它問題：Batk2不動作",
    ]


def test_all_three_other_fields_use_the_same_selected_rows_textareas(monkeypatch) -> None:
    if not RECORDING.exists():
        pytest.skip("錄製 HAR 不在本機")
    entries = json.loads(RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    _, soup = _parse_maximo_markup(entries[363]["response"]["content"]["text"])
    for column, value in ((3, "其它問題"), (4, "其它原因"), (5, "其它")):
        control = soup.find(id=f"me0c66d4a_tdrow_[C:{column}]_txt-tb[R:1]")
        assert control is not None
        control["value"] = value
    selected_detail = (
        '<component id="me0c66d4a_tbod_tdrow-tr[R:1]_holder">'
        "<script>row.setAttribute('currentrow', 'true');</script></component>"
        '<component><textarea id="md2f00fc8-ta">其它故障現象測試</textarea></component>'
        '<component><label for="m74d23c3a-ta">其它故障原因:</label>'
        '<textarea id="m74d23c3a-ta">其它故障原因測試</textarea></component>'
        '<component><label for="m73bff823-ta">其它處置措施:</label>'
        '<textarea id="m73bff823-ta">其它處置措施測試</textarea></component>'
    )
    responses = iter(
        [entries[index]["response"]["content"]["text"] for index in (341, 345, 346, 348, 349, 353)]
        + [str(soup), selected_detail]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(reader.events, "load_app", lambda **kwargs: state)
    monkeypatch.setattr(reader.events, "post", lambda **kwargs: next(responses))

    result = reader.run("115-C2-41266")

    assert result["count"] == 2
    assert result["records"][0]["故障原因"] == "不良"
    assert result["records"][0]["處置措施"] == "更換"
    assert result["records"][1]["故障現象"] == "其它問題：其它故障現象測試"
    assert result["records"][1]["故障原因"] == "其它原因：其它故障原因測試"
    assert result["records"][1]["處置措施"] == "其它：其它處置措施測試"


def test_tool_rejects_wrong_argument_count_without_loading_config(monkeypatch, capsys) -> None:
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: pytest.fail("unexpected config load"))
    assert tool.main([]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "MMISClientError"


def test_invalid_work_order_fails_before_app_load(monkeypatch) -> None:
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=None))
    monkeypatch.setattr(reader.events, "load_app", lambda **kwargs: pytest.fail("unexpected app load"))
    with pytest.raises(MMISClientError, match="工作單號"):
        reader.run("115/C2/41266")
