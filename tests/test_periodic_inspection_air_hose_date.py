from __future__ import annotations

import json
from html import escape
from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.periodic_inspection.reader import (
    PeriodicInspectionWorkOrderDetailReader,
    _vehicle_filter,
)
from tools.mmis_development import (
    query_periodic_inspection_work_order_air_hose_date as tool,
)


WORK_ORDER = "115-3A-68700-001"
STATE = PageState("session", 3, "csrf", "zz_pmwo", "https://example.test/app")
RECORDING_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-10-27_query-periodic-inspection-work-order-air-hose-date"
    r"\dom\2026-10-27T025911-318.html"
)
FIELDS = (
    "順序", "系統分類", "裝置元件", "檢查項目", "檢修標準(下限)",
    "檢修標準(上限)", "默認值", "量測值", "備註",
)


def _detail(vehicle: str) -> str:
    return (
        f'<label for="order">工作單:</label><input id="order" value="{WORK_ORDER}">'
        f'<label id="vehicle-label" for="vehicle">車組/車號:</label>'
        f'<input id="vehicle" aria-labelledby="vehicle-label" value="{vehicle}">'
        '<li ctype="tab" id="report-tab"><a title="檢修回報"></a></li>'
    )


def _appendix_page(
    rows: list[dict[str, str]],
    *,
    start: int = 1,
    total: int | None = None,
    next_page: bool = False,
    filter_open: bool = True,
) -> str:
    total = len(rows) if total is None else total
    page_range = (
        f"{start} - {start + len(rows) - 1}/{total}" if total else "0 - 0/0"
    )
    headers = "".join(
        f'<span id="appendix_ttrow_[C:{column}]_ttitle-lb">{field}</span>'
        for column, field in enumerate(FIELDS, 1)
    )
    body = "".join(
        f'<tr id="appendix_tbod_tdrow-tr[R:{index}]">'
        + "".join(
            f'<td id="appendix_tdrow_[C:{column}]-c[R:{index}]">'
            f'<span title="{escape(row.get(field, ""), quote=True)}"></span></td>'
            for column, field in enumerate(FIELDS, 1)
        )
        + "</tr>"
        for index, row in enumerate(rows)
    )
    toggle = (
        '<span ctype="label" id="appendix-lb2" targetid="appendix-lb2">過濾器</span>'
        if not filter_open else ""
    )
    filter_input = (
        '<input id="appendix_tfrow_[C:4]_txt-tb" value="">'
        if filter_open else ""
    )
    next_target = (
        '<a id="appendix-ti7"><img id="appendix-ti7_img" '
        'src="tablebtn_next_on.gif"></a>'
        if next_page else ""
    )
    return (
        f'<label class="tCount" id="appendix-lb3">{page_range}</label>'
        f'{toggle}{filter_input}{next_target}'
        '<table id="appendix_tbod-tbd" summary="附表資訊-附表(檢查數值)">'
        f'{headers}{body}</table>'
    )


class _AirHoseEvents:
    def __init__(self, vehicle: str, pages: list[str]) -> None:
        self.vehicle = vehicle
        self.pages = pages
        self.page_index = 0
        self.calls: list[tuple[str, str, str]] = []
        self.keyword = {"6": "安裝日期", "7": "空氣軟管", "8": "空氣軟管"}.get(
            vehicle[3] if len(vehicle) > 3 else "", ""
        )

    def load_app_with_response(self, **kwargs):
        assert kwargs["app_value"] == "ZZ_PMWO"
        return STATE, self._list_page()

    @staticmethod
    def _list_page() -> str:
        return (
            '<label id="list-lb3" class="tCount">1 - 1/1</label>'
            '<table id="list_tbod-tbd" summary="工作單">'
            '<span id="list_ttrow_[C:5]_ttitle-lb">工作單</span>'
            '<tr id="list_tbod_tdrow-tr[R:0]">'
            '<td id="list_tdrow_[C:5]-c[R:0]">'
            f'<span title="{WORK_ORDER}">{WORK_ORDER}</span></td></tr></table>'
        )

    def post(self, **kwargs):
        event_type = kwargs["event_type"]
        target = kwargs["target_id"]
        value = kwargs["value"]
        self.calls.append((event_type, target, value))
        if target == "list_tfrow_[C:5]_txt-tb" and event_type == "setvalue":
            return ""
        if target == "list_tbod_tfrow-tr" and event_type == "filterrows":
            return self._list_page()
        if target == "list_tdrow_[C:5]_ttxt-lb[R:0]":
            return _detail(self.vehicle)
        if target == "report-tab":
            return '<li ctype="tab" id="appendix-tab"><a title="附表一"></a></li>'
        if target == "appendix-tab":
            return self.pages[0].replace(
                '<span ctype="label" id="appendix-lb2" targetid="appendix-lb2">過濾器</span>',
                '<span ctype="label" id="appendix-lb2" targetid="appendix-lb2">過濾器</span>',
            )
        if target == "appendix-lb2":
            return self.pages[0].replace(
                '<span ctype="label" id="appendix-lb2" targetid="appendix-lb2">過濾器</span>',
                '<span ctype="label" id="appendix-lb2" targetid="appendix-lb2">過濾器</span>'
                '<input id="appendix_tfrow_[C:4]_txt-tb" value="">',
            )
        if target == "appendix-ti7":
            self.page_index += 1
            return self.pages[self.page_index]
        raise AssertionError(f"Unexpected event: {event_type} {target}")

    def post_events(self, **kwargs):
        assert kwargs["events"] == [
            ("setvalue", "appendix_tfrow_[C:4]_txt-tb", self.keyword),
            ("filterrows", "appendix_tbod_tfrow-tr", ""),
        ]
        self.calls.extend(kwargs["events"])
        return self.pages[0].replace(
            '<span ctype="label" id="appendix-lb2" targetid="appendix-lb2">過濾器</span>',
            '<span ctype="label" id="appendix-lb2" targetid="appendix-lb2">過濾器</span>'
            '<input id="appendix_tfrow_[C:4]_txt-tb" value="">',
        )


def _run(vehicle: str, pages: list[str]) -> tuple[dict, _AirHoseEvents]:
    reader = PeriodicInspectionWorkOrderDetailReader(SimpleNamespace(state=STATE))
    events = _AirHoseEvents(vehicle, pages)
    reader.events = events
    return reader.run_air_hose_dates(WORK_ORDER), events


@pytest.mark.parametrize(
    ("vehicle", "expected"),
    [("EMU601", ("600型", "安裝日期")),
     ("EMU701", ("700型", "空氣軟管")),
     ("EMU813", ("800型", "空氣軟管"))],
)
def test_vehicle_model_selects_keyword(vehicle: str, expected: tuple[str, str]) -> None:
    assert _vehicle_filter(vehicle) == expected


@pytest.mark.parametrize("vehicle", ["EMU9001", "EMU6100", "EMU1600", "DRC1000", ""])
def test_unknown_vehicle_returns_normal_json_without_opening_tabs(vehicle: str) -> None:
    reader = PeriodicInspectionWorkOrderDetailReader(SimpleNamespace(state=STATE))
    events = _AirHoseEvents(vehicle, [])
    reader.events = events

    result = reader.run_air_hose_dates(WORK_ORDER)

    assert result["success"] is True
    assert result["supported"] is False
    assert result["message"] == "此工作單非支援的車型"
    assert result["records"] == []
    assert result["車組/車號"] == vehicle
    assert not any(call[1] == "report-tab" for call in events.calls)
    assert json.loads(json.dumps(result, ensure_ascii=False))["message"] == "此工作單非支援的車型"


def test_reads_all_columns_across_pages_and_opens_filter() -> None:
    first_rows = [
        {"順序": "2,430", "系統分類": "連結裝置", "裝置元件": "空氣軟管",
         "檢查項目": f"空氣軟管 項目{i}", "量測值": f"2026/01/{i:02d}"}
        for i in range(1, 3)
    ]
    last_row = {
        "順序": "2,450", "系統分類": "連結裝置", "裝置元件": "空氣軟管",
        "檢查項目": "空氣軟管 項目3", "量測值": "",
    }
    result, events = _run("EMU813", [
        _appendix_page(first_rows, start=1, total=3, next_page=True, filter_open=False),
        _appendix_page([last_row], start=3, total=3),
    ])

    assert result["count"] == 3
    assert result["車型"] == "800型"
    assert result["filter_keyword"] == "空氣軟管"
    assert len(result["records"]) == 3
    assert set(result["records"][0]) == {"檢查項目", "量測值"}
    assert result["records"][-1]["量測值"] == ""
    assert ("click", "appendix-lb2", "") in events.calls
    assert ("click", "appendix-ti7", "") in events.calls


def test_600_model_filters_installation_date_and_accepts_no_matches() -> None:
    result, _ = _run(
        "EMU601",
        [_appendix_page([], total=0)],
    )

    assert result["車型"] == "600型"
    assert result["filter_keyword"] == "安裝日期"
    assert result["count"] == 0
    assert result["records"] == []


def test_rejects_rows_outside_selected_filter() -> None:
    row = {"檢查項目": "其他項目", "量測值": "2026/01/01"}
    with pytest.raises(MMISClientError, match="不符合關鍵字"):
        _run("EMU813", [_appendix_page([row])])


def test_preserves_html_entities_and_blank_measurements() -> None:
    row = {
        "檢查項目": "空氣軟管 & 接頭",
        "量測值": "",
        "備註": "檢查 <完成>",
    }
    result, _ = _run("EMU813", [_appendix_page([row])])

    assert result["records"][0]["檢查項目"] == "空氣軟管 & 接頭"
    assert result["records"][0]["量測值"] == ""
    assert set(result["records"][0]) == {"檢查項目", "量測值"}


@pytest.mark.skipif(not RECORDING_DOM.exists(), reason="本機未提供指定 Recorder DOM")
def test_recorded_appendix_has_thirteen_rows_and_nine_data_headers() -> None:
    from mmis_connector.parser import parse_maximo_table

    schema, rows = parse_maximo_table(
        RECORDING_DOM.read_text(encoding="utf-8"),
        required_headers={"檢查項目", "量測值"},
        table_summary="附表資訊-附表(檢查數值)",
    )

    assert schema is not None
    assert len(rows) == 13
    assert len(schema.headers) == 9
    assert {"檢查項目", "量測值"}.issubset(schema.headers.values())


def test_tool_rejects_wrong_arg_count_before_loading_config(monkeypatch, capsys) -> None:
    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: pytest.fail("unexpected config load"))
    assert tool.main([]) == 1
    error = json.loads(capsys.readouterr().out)
    assert error["error"] == "MMISClientError"
