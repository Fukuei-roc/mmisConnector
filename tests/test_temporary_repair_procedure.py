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
    parse_temporary_repair_basic_info,
    parse_temporary_repair_linked_fault_notices,
    parse_temporary_repair_test_run_page,
)
from tools.mmis_development import (
    query_temporary_repair_work_order_detail as tool,
)


RECORDING = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-05_query-temporary-repair-work-order-maintenance-procedure-summary"
    r"\raw.har"
)
BASIC_RECORDING = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-05_query-temporary-repair-work-order-basic-information"
    r"\raw.har"
)
BASIC_DOM = BASIC_RECORDING.parent / "dom" / "2026-10-05T060838-420.html"
OPTIMIZATION_RECORDING = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-05_optimize-temporary-repair-work-order-query-speed"
    r"\raw.har"
)
TEST_RUN_RECORDING = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-07_query-whether-temporary-repair-work-order-includes-test-run-order"
    r"\raw.har"
)


def test_recorded_test_run_page_reads_requested_six_fields() -> None:
    if not TEST_RUN_RECORDING.exists():
        pytest.skip("試車報告錄製 HAR 不在本機")
    entries = json.loads(TEST_RUN_RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    records, page = parse_temporary_repair_test_run_page(
        entries[355]["response"]["content"]["text"]
    )
    assert page.total == 1
    assert records == [{
        "工作單": "115-C2-41283-001", "檢修內容": "試車報告",
        "車組/車號": "EMU939", "檢修廠段": "MHY10",
        "檢修單位": "檢查室", "工作單狀態": "核簽中",
    }]


def _test_run_table(rows: list[tuple[str, ...]], *, total: int | None = None) -> str:
    headers = ("工作單", "檢修內容", "車組/車號", "檢修廠段", "檢修單位", "工作單狀態")
    count = len(rows) if total is None else total
    end = len(rows)
    parts = [
        '<table summary="工作單的子項 123" id="child_tbod-tbd">',
        '<span class="tCount" id="child-lb3">'
        + (f"1 - {end}/{count}" if count else "0 - 0/0") + "</span>",
    ]
    parts.extend(
        f'<span id="child_ttrow_[C:{column}]_ttitle-lb">{header}</span>'
        for column, header in enumerate(headers, 1)
    )
    for index, values in enumerate(rows):
        parts.append(f'<tr id="child_tbod_tdrow-tr[R:{index}]">')
        for column, value in enumerate(values, 1):
            parts.append(
                f'<td id="child_tdrow_[C:{column}]-c[R:{index}]">'
                f'<input id="child_tdrow_[C:{column}]_txt-tb[R:{index}]" value="{value}">'
                "</td>"
            )
        parts.append("</tr>")
    parts.append("</table>")
    if count > end:
        parts.append('<a id="child-ti1"><img id="child-ti1_img" src="tablebtn_next_on.gif"></a>')
    return "".join(parts)


def test_test_run_page_filters_other_children_and_keeps_multiple_reports() -> None:
    html = _test_run_table([
        ("115-C2-41283-001", "試車報告", "EMU939", "MHY10", "檢查室", "核簽中"),
        ("115-C2-41283-002", "一般檢修", "EMU939", "MHY10", "檢查室", "完成"),
        ("115-C2-41283-003", "試車報告", "EMU939", "MHY10", "檢查室", "完成"),
    ])
    records, page = parse_temporary_repair_test_run_page(html)
    assert page.total == 3
    assert [row["工作單"] for row in records] == [
        "115-C2-41283-001", "115-C2-41283-003"
    ]
    assert records[0] == {
        "工作單": "115-C2-41283-001", "檢修內容": "試車報告",
        "車組/車號": "EMU939", "檢修廠段": "MHY10",
        "檢修單位": "檢查室", "工作單狀態": "核簽中",
    }


def test_test_run_page_accepts_empty_child_table() -> None:
    records, page = parse_temporary_repair_test_run_page(_test_run_table([]))
    assert records == []
    assert page.total == 0


def test_test_run_page_ignores_other_child_work_orders() -> None:
    records, page = parse_temporary_repair_test_run_page(_test_run_table([
        ("115-C2-41283-002", "一般檢修", "EMU939", "MHY10", "檢查室", "完成"),
    ]))
    assert records == []
    assert page.total == 1


def test_test_run_page_exposes_next_page_target() -> None:
    _, page = parse_temporary_repair_test_run_page(_test_run_table([
        ("115-C2-41283-001", "試車報告", "EMU939", "MHY10", "檢查室", "核簽中"),
    ], total=2))
    assert page.next_page_target == "child-ti1"


def test_test_run_page_rejects_incomplete_child_page() -> None:
    with pytest.raises(MMISClientError, match="分頁範圍"):
        parse_temporary_repair_test_run_page(
            _test_run_table([
                ("115-C2-41283-001", "試車報告", "EMU939", "MHY10", "檢查室", "核簽中")
            ]).replace("1 - 1/1", "1 - 2/2")
        )


def _recorded_query_calls(
    monkeypatch, *, number: str, response_indices: tuple[int, ...]
) -> list[dict[str, Any]]:
    entries = json.loads(OPTIMIZATION_RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(
        reader.events,
        "load_app_with_response",
        lambda **kwargs: (state, entries[252]["response"]["content"]["text"]),
    )
    responses = iter(
        entries[index]["response"]["content"]["text"]
        for index in response_indices
    )
    calls: list[dict[str, Any]] = []

    def post(**kwargs: Any) -> str:
        calls.append(kwargs)
        if kwargs["target_id"].endswith("_ttxt-lb[R:0]"):
            raise RuntimeError("detail clicked")
        return next(responses)

    monkeypatch.setattr(reader.events, "post", post)
    with pytest.raises(RuntimeError, match="detail clicked"):
        reader.run(number)
    return calls


def test_recorded_query_uses_default_list_before_all_records(monkeypatch) -> None:
    if not OPTIMIZATION_RECORDING.exists():
        pytest.skip("速度優化錄製 HAR 不在本機")
    calls = _recorded_query_calls(
        monkeypatch, number="115-C1-41264", response_indices=(340, 343, 344)
    )

    assert [(call["event_type"], call["value"]) for call in calls] == [
        ("setvalue", "115-C1-41264"),
        ("setvalue", "C1,C2,C3"),
        ("filterrows", ""),
        ("click", ""),
    ]
    assert [call["xhr_seq"] for call in calls] == [1, 2, 3, 4]


def test_recorded_query_falls_back_to_all_records_only_after_zero(monkeypatch) -> None:
    if not OPTIMIZATION_RECORDING.exists():
        pytest.skip("速度優化錄製 HAR 不在本機")
    calls = _recorded_query_calls(
        monkeypatch,
        number="115-C1-36682",
        response_indices=(340, 343, 348, 353, 356, 362, 363, 364),
    )

    assert [(call["event_type"], call["value"]) for call in calls] == [
        ("setvalue", "115-C1-36682"),
        ("setvalue", "C1,C2,C3"),
        ("filterrows", ""),
        ("click", ""),
        ("click", "useAllRecsQuery_OPTION"),
        ("setvalue", "115-C1-36682"),
        ("setvalue", "C1,C2,C3"),
        ("filterrows", ""),
        ("click", ""),
    ]
    assert [call["xhr_seq"] for call in calls] == list(range(1, 10))


def test_recorded_query_reports_missing_only_after_all_records(monkeypatch) -> None:
    if not OPTIMIZATION_RECORDING.exists():
        pytest.skip("速度優化錄製 HAR 不在本機")
    entries = json.loads(OPTIMIZATION_RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(
        reader.events,
        "load_app_with_response",
        lambda **kwargs: (state, entries[252]["response"]["content"]["text"]),
    )
    responses = iter(
        entries[index]["response"]["content"]["text"]
        for index in (340, 343, 348, 353, 356, 362, 363, 348)
    )
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "post", post)
    with pytest.raises(MMISClientError, match="找不到工作單：115-C1-36682"):
        reader.run("115-C1-36682")
    assert len(calls) == 8


def test_inconsistent_first_query_does_not_switch_to_all_records(monkeypatch) -> None:
    if not OPTIMIZATION_RECORDING.exists():
        pytest.skip("速度優化錄製 HAR 不在本機")
    entries = json.loads(OPTIMIZATION_RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    _, soup = _parse_maximo_markup(entries[344]["response"]["content"]["text"])
    count = soup.find(id="m6a7dfd2f-lb3")
    assert count is not None
    count.string = "1 - 1/2"
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(
        reader.events,
        "load_app_with_response",
        lambda **kwargs: (state, entries[252]["response"]["content"]["text"]),
    )
    responses = iter([
        entries[index]["response"]["content"]["text"] for index in (340, 343)
    ] + [str(soup)])
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "post", post)
    with pytest.raises(MMISClientError, match="不是唯一一筆"):
        reader.run("115-C1-41264")
    assert [call["event_type"] for call in calls] == ["setvalue", "setvalue", "filterrows"]


def test_recorded_c1_detail_reads_linked_fault_notice() -> None:
    if not BASIC_RECORDING.exists():
        pytest.skip("基本資料錄製 HAR 不在本機")
    entries = json.loads(BASIC_RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    detail = entries[352]["response"]["content"]["text"]

    assert parse_temporary_repair_linked_fault_notices(detail) == {
        "count": 1,
        "records": [{
            "故障通報號": "1151005-29",
            "發生日期": "2026/10/03",
            "車組/車號": "EMA815",
            "故障現象": "TCMS未接收BECU傳輸信號,2車 Ma815 BECU 故障",
            "事故等級": "A",
        }],
    }


def test_linked_fault_notice_rejects_incomplete_page() -> None:
    if not BASIC_RECORDING.exists():
        pytest.skip("基本資料錄製 HAR 不在本機")
    entries = json.loads(BASIC_RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    _, soup = _parse_maximo_markup(entries[352]["response"]["content"]["text"])
    count = soup.find(id="m31d0c5ac-lb3")
    assert count is not None
    count.string = "1 - 1/2"

    with pytest.raises(MMISClientError, match="拒絕回傳不完整資料"):
        parse_temporary_repair_linked_fault_notices(str(soup))


@pytest.mark.parametrize("source", ["har", "dom"])
def test_basic_information_recording_has_all_eight_visible_fields(source) -> None:
    if not BASIC_RECORDING.exists() or not BASIC_DOM.exists():
        pytest.skip("基本資料錄製證據不在本機")
    if source == "har":
        entries = json.loads(BASIC_RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
        response = entries[352]["response"]["content"]["text"]
    else:
        response = BASIC_DOM.read_text(encoding="utf-8")

    basic = parse_temporary_repair_basic_info(response)

    assert {key: value for key, value in basic.items() if key != "備註"} == {
        "車組/車號": "EMU815",
        "檢修級別": "C1",
        "故障現象": "10/3-4252次EMA815不鬆軔事故",
        "原因說明": "BECU單元故障，無不鬆軔情形",
        "檢修日期": "2026/10/05",
        "完工日期": "2026/10/05",
        "工作單狀態": "完工待回報",
    }
    assert basic["備註"].startswith("1.庫內啟動測試EMA815")
    assert "\n2." in basic["備註"] and "\n3." in basic["備註"]


def test_basic_information_rejects_conflicting_duplicate_dates() -> None:
    if not BASIC_DOM.exists():
        pytest.skip("基本資料錄製 DOM 不在本機")
    _, soup = _parse_maximo_markup(BASIC_DOM.read_text(encoding="utf-8"))
    date_labels = [
        label for label in soup.find_all("label", attrs={"for": True})
        if label.get_text(" ", strip=True).rstrip(":：").strip() == "檢修日期"
    ]
    assert len(date_labels) == 2
    second = soup.find("input", id=date_labels[1]["for"])
    assert second is not None
    second["title"] = "2026/10/06"

    with pytest.raises(MMISClientError, match="檢修日期缺失或不一致"):
        parse_temporary_repair_basic_info(str(soup))


def test_recorded_flow_reads_two_rows_and_only_requested_fields(monkeypatch) -> None:
    if not RECORDING.exists():
        pytest.skip("錄製 HAR 不在本機")
    entries = json.loads(RECORDING.read_text(encoding="utf-8"))["log"]["entries"]
    responses = iter(entries[index]["response"]["content"]["text"] for index in (346, 348, 349, 353, 363))
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    client = SimpleNamespace(state=state)
    reader = TemporaryRepairProcedureReader(client)
    calls = []

    def load_app(**kwargs):
        assert kwargs["app_value"] == "ZZ_CMWO"
        return state, entries[345]["response"]["content"]["text"]

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "load_app_with_response", load_app)
    monkeypatch.setattr(reader.events, "post", post)

    result = reader.run(" 115-C2-41266 ")

    assert result["success"] is True
    assert result["query_name"] == "查詢臨時檢修工單明細"
    assert result["work_order"] == "115-C2-41266"
    assert result["車組/車號"] == "ED813"
    assert result["檢修級別"] == "C2"
    assert result["已勾稽故障通報"] == {"count": 0, "records": []}
    assert list(result).index("工作單狀態") < list(result).index("已勾稽故障通報")
    assert list(result).index("已勾稽故障通報") < list(result).index("維修程序概況")
    assert list(result)[-1] == "試車報告"
    assert result["試車報告"] == {"count": 0, "records": []}
    assert "count" not in result and "records" not in result
    summary = result["維修程序概況"]
    assert summary["count"] == 2
    assert [row["車組/車號"] for row in summary["records"]] == ["ED813", "ED813"]
    assert [row["故障類別"] for row in summary["records"]] == ["911", "111"]
    assert [row["材料編號(PA)"] for row in summary["records"]] == ["1780011124", "120338212D"]
    assert [row["更換數量"] for row in summary["records"]] == ["1.00", "1.00"]
    assert summary["records"][0]["故障現象"] == "其它問題：Batk2不動作"
    assert summary["records"][1]["故障現象"] == "集電舟碳刷撞損"
    assert all(len(row) == 9 and "故障類別說明" in row for row in summary["records"])
    assert [(call["event_type"], call["value"]) for call in calls] == [
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
        [entries[index]["response"]["content"]["text"] for index in (346, 348, 349, 353)]
        + [str(soup)]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(reader.events, "load_app_with_response", lambda **kwargs: (state, entries[345]["response"]["content"]["text"]))
    monkeypatch.setattr(reader.events, "post", lambda **kwargs: next(responses))

    result = reader.run("115-C2-41266")

    assert result["維修程序概況"] == {"count": 0, "records": []}
    assert result["試車報告"] == {"count": 0, "records": []}


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
        [entries[index]["response"]["content"]["text"] for index in (346, 348, 349, 353)]
        + [str(soup), selected_detail]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    calls = []
    monkeypatch.setattr(reader.events, "load_app_with_response", lambda **kwargs: (state, entries[345]["response"]["content"]["text"]))

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader.events, "post", post)

    result = reader.run("115-C2-41266")

    records = result["維修程序概況"]["records"]
    assert records[0]["故障現象"] == "其它問題：Batk2不動作"
    assert records[1]["故障現象"] == "其它問題：第二列補充"
    assert calls[-1]["target_id"] == "me0c66d4a_tdrow_[C:0]_tgdet-ti[R:1]"
    assert calls[-1]["xhr_seq"] == 6


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
        [entries[index]["response"]["content"]["text"] for index in (346, 348, 349, 353)]
        + [str(soup), unchanged_detail]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(reader.events, "load_app_with_response", lambda **kwargs: (state, entries[345]["response"]["content"]["text"]))
    monkeypatch.setattr(reader.events, "post", lambda **kwargs: next(responses))

    result = reader.run("115-C2-41266")

    assert [row["故障現象"] for row in result["維修程序概況"]["records"]] == [
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
        [entries[index]["response"]["content"]["text"] for index in (346, 348, 349, 353)]
        + [str(soup), selected_detail]
    )
    state = PageState("session", 3, "csrf", "zz_cmwo", "https://example.test/app")
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=state))
    monkeypatch.setattr(reader.events, "load_app_with_response", lambda **kwargs: (state, entries[345]["response"]["content"]["text"]))
    monkeypatch.setattr(reader.events, "post", lambda **kwargs: next(responses))

    result = reader.run("115-C2-41266")

    summary = result["維修程序概況"]
    assert summary["count"] == 2
    assert summary["records"][0]["故障原因"] == "不良"
    assert summary["records"][0]["處置措施"] == "更換"
    assert summary["records"][1]["故障現象"] == "其它問題：其它故障現象測試"
    assert summary["records"][1]["故障原因"] == "其它原因：其它故障原因測試"
    assert summary["records"][1]["處置措施"] == "其它：其它處置措施測試"


def test_tool_rejects_wrong_argument_count_without_loading_config(monkeypatch, capsys) -> None:
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: pytest.fail("unexpected config load"))
    assert tool.main([]) == 1
    error = json.loads(capsys.readouterr().out)
    assert error["error"] == "MMISClientError"
    assert "query_temporary_repair_work_order_detail <工作單號>" in error["message"]


def test_invalid_work_order_fails_before_app_load(monkeypatch) -> None:
    reader = TemporaryRepairProcedureReader(SimpleNamespace(state=None))
    monkeypatch.setattr(reader.events, "load_app_with_response", lambda **kwargs: pytest.fail("unexpected app load"))
    with pytest.raises(MMISClientError, match="工作單號"):
        reader.run("115/C2/41266")
