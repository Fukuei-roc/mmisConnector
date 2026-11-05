from __future__ import annotations

from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.periodic_inspection.status import (
    CompletePeriodicInspectionWorkOrderStatusQuery,
)
from tools.mmis_development import (
    query_complete_periodic_inspection_work_order_status as tool,
)


STATE = PageState("session", 3, "csrf", "zz_pmwo", "https://example.test/app")
HEADERS = {
    1: "車組/車號",
    3: "檢修級別",
    5: "工作單",
    7: "檢修單位",
    8: "工作單狀態",
    17: "母工單",
}


def table(
    rows: list[tuple[str, str, str, str, str, str]],
    *,
    start: int = 1,
    total: int | None = None,
    next_page: bool = False,
) -> str:
    total = len(rows) if total is None else total
    headers = "".join(
        f'<span id="list_ttrow_[C:{column}]_ttitle-lb">{label}</span>'
        for column, label in HEADERS.items()
    )
    rendered = []
    for index, values in enumerate(rows):
        cells = "".join(
            f'<td id="list_tdrow_[C:{column}]-c[R:{index}]">'
            f'<span id="list_{column}_ttxt-lb[R:{index}]">{value}</span></td>'
            for column, value in zip(HEADERS, values)
        )
        rendered.append(f'<tr id="list_tbod_tdrow-tr[R:{index}]">{cells}</tr>')
    end = start + len(rows) - 1 if rows else 0
    count = f'<label id="list-lb3" class="tCount">{start if rows else 0} - {end}/{total}</label>'
    next_button = (
        '<a id="list-ti2"><img id="list-ti2_img" src="tablebtn_next_on.gif"></a>'
        if next_page else ""
    )
    return headers + count + "".join(rendered) + next_button + ("沒有要顯示的列。" if not rows else "")


def query(monkeypatch: pytest.MonkeyPatch, *pages: str):
    instance = CompletePeriodicInspectionWorkOrderStatusQuery(SimpleNamespace(state=STATE))
    responses = iter(["mainrec_menus", table([]), "", "", *pages])
    calls = []
    monkeypatch.setattr(instance.events, "load_app_with_response", lambda **kwargs: (STATE, ""))

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(instance.events, "post", post)
    return instance, calls


def test_returns_all_child_statuses_across_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    first = table(
        [("EMU815", "3A", "115-3A-75840-001", "檢查室", "待簽核", "0")],
        total=3,
        next_page=True,
    )
    last = table(
        [
            ("EMU815", "3A", "115-3A-75840-002", "檢修場", "執行結案", "0"),
            ("EMU815", "TR", "115-3A-75840-003", "檢查室", "待簽核", "0"),
        ],
        start=2,
        total=3,
    )
    instance, calls = query(monkeypatch, first, last)

    result = instance.run(" 115-3A-75840 ")

    assert result["work_order"] == "115-3A-75840"
    assert result["count"] == 3
    assert [record["工作單"] for record in result["records"]] == [
        "115-3A-75840-001", "115-3A-75840-002", "115-3A-75840-003"
    ]
    assert result["records"][2]["檢修級別"] == "TR"
    assert [(call["event_type"], call["value"]) for call in calls] == [
        ("click", ""), ("click", "useAllRecsQuery_OPTION"),
        ("setvalue", "115-3A-75840"), ("setvalue", "0"),
        ("filterrows", ""), ("click", ""),
    ]
    assert calls[2]["target_id"] == "list_tfrow_[C:5]_txt-tb"
    assert calls[3]["target_id"] == "list_tfrow_[C:17]_txt-tb"
    assert calls[4]["current_focus"] == "list_tfrow_[C:5]_txt-tb"


def test_empty_result_is_one_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    instance, _ = query(monkeypatch, table([]))
    assert instance.run("115-2A-74886")["records"] == []


def test_preserves_blank_status_instead_of_losing_the_row(monkeypatch: pytest.MonkeyPatch) -> None:
    instance, _ = query(
        monkeypatch,
        table([("EMU721", "2A", "115-2A-74886-001", "檢查室", "", "0")]),
    )
    result = instance.run("115-2A-74886")
    assert result["records"][0]["工作單狀態"] == ""


@pytest.mark.parametrize("wrong", [
    ("EMU815", "3A", "115-3A-758400-001", "檢查室", "待簽核", "0"),
    ("EMU815", "3A", "115-3A-75840-001", "檢查室", "待簽核", "1"),
])
def test_rejects_unrelated_rows(monkeypatch: pytest.MonkeyPatch, wrong) -> None:
    instance, _ = query(monkeypatch, table([wrong]))
    with pytest.raises(MMISClientError, match="結果與查詢條件不符"):
        instance.run("115-3A-75840")


def test_rejects_incomplete_page(monkeypatch: pytest.MonkeyPatch) -> None:
    instance, _ = query(
        monkeypatch,
        table([("EMU815", "3A", "115-3A-75840-001", "檢查室", "待簽核", "0")], total=2),
    )
    with pytest.raises(MMISClientError, match="尚未讀完"):
        instance.run("115-3A-75840")


def test_cli_rejects_multiple_inputs_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert tool.main(["115-3A-75840", "115-2A-74886"]) == 1
    assert '"success": false' in capsys.readouterr().out
