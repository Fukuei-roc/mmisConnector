from __future__ import annotations

import json
from pathlib import Path

import pytest

from mmis_connector.auth import MMISClientError
from mmis_connector.fault_notices.atp_options import (
    ATPOptionsExporter,
    parse_lookup_page,
    write_export,
)


def page(names: list[str], start: int = 1, total: int | None = None, next_page: bool = False) -> str:
    total = len(names) if total is None else total
    rows = "".join(
        f'<tr id="lookup_page1_tbod_tdrow-tr[R:{i}]">'
        f'<td id="lookup_page1_tdrow_[C:0]-c[R:{i}]">'
        f'<a id="lookup_page1_tdrow_[C:0]_ttxt-lb[R:{i}]">{name}</a></td></tr>'
        for i, name in enumerate(names)
    )
    next_button = ('<a id="lookup_page1-ti2"><img id="lookup_page1-ti2_img" '
                   'src="tablebtn_next_on.gif"></a>') if next_page else ""
    end = start + len(names) - 1 if names else 0
    start = start if names else 0
    return (f'<table id="lookup_page1-to"><span id="lookup_page1_ttrow_[C:0]_ttitle-lb">名稱</span>'
            f'{rows}</table><span class="tCount" id="lookup_page1-lb3">{start} - {end}/{total}</span>'
            f'{next_button}<button id="cancel-pb">取消</button>')


def test_recorded_lookup_shape_and_pagination() -> None:
    # Same lookup_page1 table/row/count controls as the recorded Maximo response.
    first, info = parse_lookup_page(page(["其它", "人為因素"], total=3, next_page=True))
    second, final = parse_lookup_page(page(["設備故障"], start=3, total=3))
    assert [x["name"] for x in first + second] == ["其它", "人為因素", "設備故障"]
    assert info.next_page_target == "lookup_page1-ti2"
    assert final.total == 3 and final.next_page_target is None
    assert all(x["code"] is None for x in first + second)


def test_sanitized_recording_fixture() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "atp_lookup_recorded.json").read_text(encoding="utf-8"))
    assert [entry["page_total"] for entry in fixture] == [6, 2, 1]
    assert fixture[0]["names"] == ["其它", "人為因素", "外部干擾", "設備故障", "不明原因", "非ATP故障"]
    for entry in fixture:
        options, info = parse_lookup_page(page(entry["names"]))
        assert [option["name"] for option in options] == entry["names"]
        assert info.total == entry["page_total"]


def test_bad_response_is_not_empty() -> None:
    with pytest.raises(MMISClientError):
        parse_lookup_page("<server_response></server_response>")
    with pytest.raises(MMISClientError):
        parse_lookup_page(page(["a"], total=2))


def test_confirmed_empty_lookup() -> None:
    markup = page([]) + "沒有要顯示的列"
    options, info = parse_lookup_page(markup)
    assert options == [] and info.total == 0


def test_export_tree_and_partial_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exporter = ATPOptionsExporter(object(), delay_seconds=0)
    lists = {
        "故障要因": [{"name": "甲", "code": None}, {"name": "乙", "code": None}],
        "故障因子": [{"name": "同名", "code": None}],
        "故障項目": [{"name": "同名", "code": None}],
    }
    monkeypatch.setattr("mmis_connector.fault_notices.atp_options.FaultNoticeAnalysisReader._load_exact_detail",
                        lambda self, notice: (None, "detail"))
    monkeypatch.setattr("mmis_connector.fault_notices.atp_options.parse_atp_fault_checked", lambda _: True)
    monkeypatch.setattr("mmis_connector.fault_notices.atp_options.parse_maximo_tab_target",
                        lambda markup, title: "fake-tab")
    monkeypatch.setattr(exporter, "_post", lambda **kwargs: "detail")
    monkeypatch.setattr("mmis_connector.fault_notices.atp_options._field_controls", lambda _: {})
    monkeypatch.setattr(exporter, "_open", lambda field: lists[field])
    monkeypatch.setattr(exporter, "_choose", lambda *args: None)
    result = exporter.run("1151012-36")
    assert result["statistics"] == {"causes": 2, "factors": 2, "items": 2, "valid_combinations": 2}
    assert result["fault_causes"][0]["factors"][0]["items"][0]["name"] == "同名"
    assert result["fault_causes"][1]["factors"][0]["name"] == "同名"
    output = tmp_path / "atp_fault_analysis_options.json"
    write_export(result, output)
    assert json.loads(output.read_text(encoding="utf-8"))["traversal_status"] == "completed"

    def fail_item(field: str):
        if field == "故障項目":
            raise MMISClientError("暫時失敗")
        return lists[field]
    monkeypatch.setattr(exporter, "_open", fail_item)
    partial = exporter.run("1151012-36")
    assert partial["traversal_status"] == "partial"
    assert partial["statistics"]["valid_combinations"] == 0
    assert partial["fault_causes"][0]["factors"][0]["items"] is None
    partial_path = write_export(partial, output)
    assert partial_path.name.endswith(".partial.json")
    assert json.loads(output.read_text(encoding="utf-8"))["traversal_status"] == "completed"


def test_event_allowlist_rejects_business_write() -> None:
    class Dummy:
        state = object()
    exporter = ATPOptionsExporter(Dummy(), delay_seconds=0)
    with pytest.raises(MMISClientError, match="禁止"):
        exporter._post(focus="save", target="save")


def test_partial_cli_returns_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from tools.mmis_development import export_atp_fault_analysis_options as tool

    monkeypatch.setattr(tool, "execute", lambda args: {"success": False, "traversal_status": "partial"})
    assert tool.main(["1151012-36"]) == 2
    assert json.loads(capsys.readouterr().out)["traversal_status"] == "partial"
