from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.repair_work_orders import FIELDS, RepairWorkOrdersReader
from mmis_connector.parser import parse_maximo_page_info, parse_maximo_table


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings\2026-10-02_query-repair-work-orders-linked-to-fault-notice\dom\2026-10-02T045548-431.html"
)


def _table(numbers: list[str], *, start: int = 1, total: int | None = None) -> str:
    total = len(numbers) if total is None else total
    headers = "".join(
        f'<span id="orders_ttrow_[C:{i}]_ttitle-lb">{name}</span>'
        for i, name in enumerate(FIELDS, 1)
    )
    rows = "".join(
        f'<tr id="orders_tbod_tdrow-tr[R:{row}]">'
        + "".join(
            f'<td id="orders_tdrow_[C:{col}]-c[R:{row}]">'
            f'<span title="{value}">{value}</span></td>'
            for col, value in enumerate((number, "4119", "", "", "", "", "", "", "", ""), 1)
        )
        + "</tr>"
        for row, number in enumerate(numbers)
    )
    next_control = (
        '<a id="orders-ti7"><img id="orders-ti7_img" src="tablebtn_next_on.gif"></a>'
        if start + len(numbers) - 1 < total else ""
    )
    count = f"{start} - {start + len(numbers) - 1}/{total}" if total else "0 - 0/0"
    return (
        f'<label id="orders-lb3" class="tCount">{count}</label>{next_control}'
        f'<table summary="查修工單">{headers}{rows}</table>'
    )


def _reader(monkeypatch, pages: list[str]):
    reader = RepairWorkOrdersReader(SimpleNamespace(state=STATE))
    monkeypatch.setattr(
        reader, "_load_exact_detail",
        lambda notice: (STATE, '<li id="tracking-tab" ctype="tab"><a title="故障追蹤">故障追蹤</a></li>'),
    )
    responses = iter(pages)
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader, "_post_event", post)
    return reader, calls


@pytest.mark.skipif(not RECORDED_DOM.is_file(), reason="local recording unavailable")
def test_recorded_repair_order_fields_and_date():
    html = RECORDED_DOM.read_text(encoding="utf-8")
    schema, rows = parse_maximo_table(html, required_headers=set(FIELDS), table_summary="查修工單")
    assert schema is not None
    assert parse_maximo_page_info(html, table_prefix=schema.prefix, context_name="查修工單").total == 1
    assert rows == [{
        "工作單": "115-CA-40035", "車次": "4119",
        "維修情形": "量測電源約 DC 19 V, 重置相關斷路器無效",
        "狀態判定": "返段檢修", "檢修廠段": "七堵機務段",
        "檢修日期": "2026/09/30", "檢修單位": "列檢人員",
        "檢查人員": "洪盛裕", "開單人員": "洪盛裕", "工作單狀態": "檢修完成",
    }]


def test_empty_and_multiple_pages_with_non_ca_and_duplicate(monkeypatch):
    reader, _ = _reader(monkeypatch, [_table([])])
    assert reader.run("1150930-09")["records"] == []

    reader, calls = _reader(monkeypatch, [
        _table(["115-CA-40035", "115-1A-12345"], total=4),
        _table(["115-CA-40035", "115-CA-40036"], start=3, total=4),
    ])
    result = reader.run("1150930-09")
    assert result["count"] == 2
    assert [row["工作單"] for row in result["records"]] == ["115-CA-40035", "115-CA-40036"]
    assert result["records"][0]["維修情形"] == ""
    assert [(call["target_id"], call["xhr_seq"]) for call in calls] == [
        ("tracking-tab", 3), ("orders-ti7", 4),
    ]


def test_incomplete_page_fails(monkeypatch):
    reader, _ = _reader(monkeypatch, [_table(["115-CA-40035"], total=2).replace("tablebtn_next_on.gif", "tablebtn_next_off.gif")])
    with pytest.raises(MMISClientError, match="下一頁"):
        reader.run("1150930-09")
