from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.fault_notices.linked_work_orders import LinkedWorkOrdersReader
from mmis_connector.parser import parse_maximo_page_info, parse_maximo_table


STATE = PageState("session", 3, "csrf", "zz_fnm", "https://example.test/app")
RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings\2026-10-02_query-work-orders-linked-to-fault-notice\dom\2026-10-02T023616-990.html"
)
FIELDS = {"工作單", "工單級別", "車組/車號", "工作單說明", "工作單狀態", "通報號", "狀態"}


def _table(
    numbers: list[str], *, start: int = 1, total: int | None = None,
    row_notice: str = "1150910-14", row_status: str = "處理完成",
) -> str:
    total = len(numbers) if total is None else total
    headers = "".join(
        f'<span id="orders_ttrow_[C:{i}]_ttitle-lb">{field}</span>'
        for i, field in enumerate(FIELDS_ORDERED, 1)
    )
    rows = "".join(
        f'<tr id="orders_tbod_tdrow-tr[R:{r}]">'
        + "".join(
            f'<td id="orders_tdrow_[C:{i}]-c[R:{r}]">'
            f'<span id="orders_tdrow_[C:{i}]_ttxt-lb[R:{r}]" title="{value}">{value}</span></td>'
            for i, value in enumerate((number, "C1", "EMU935", "說明", "工單結案", row_notice, row_status), 1)
        )
        + "</tr>"
        for r, number in enumerate(numbers)
    )
    next_control = '<a id="orders-ti7"><img id="orders-ti7_img" src="tablebtn_next_on.gif"></a>' if start + len(numbers) - 1 < total else ""
    count = f"{start} - {start + len(numbers) - 1}/{total}" if total else "0 - 0/0"
    return (
        '<div>沒有要顯示的列</div>'
        f'<label id="orders-lb3" class="tCount">{count}</label>{next_control}'
        f'<table summary="檢視所有段檢修工單">{headers}{rows}</table>'
    )


FIELDS_ORDERED = ("工作單", "工單級別", "車組/車號", "工作單說明", "工作單狀態", "通報號", "狀態")


def _reader(monkeypatch, pages: list[str]):
    client = SimpleNamespace(state=STATE)
    reader = LinkedWorkOrdersReader(client)
    monkeypatch.setattr(reader, "_load_exact_detail", lambda notice: (STATE, '<li id="tracking-tab" ctype="tab"><a title="故障追蹤">故障追蹤</a></li>'))
    responses = iter(pages)
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(reader, "_post_event", post)
    return reader, calls


def test_deduplicates_across_pages_and_ignores_other_empty_table(monkeypatch):
    reader, calls = _reader(monkeypatch, [_table(["115-C1-35820", "115-C2-35988"], total=4), _table(["115-C1-35820", "115-1A-70151"], start=3, total=4)])
    result = reader.run("1150910-14")
    assert result["count"] == 3
    assert [row["工作單"] for row in result["records"]] == ["115-C1-35820", "115-C2-35988", "115-1A-70151"]
    assert [(call["target_id"], call["xhr_seq"]) for call in calls] == [("tracking-tab", 3), ("orders-ti7", 4)]


def test_rejects_incomplete_pagination(monkeypatch):
    reader, _ = _reader(monkeypatch, [_table(["115-C1-35820"], total=2).replace('src="tablebtn_next_on.gif"', 'src="tablebtn_next_off.gif"')])
    with pytest.raises(MMISClientError, match="下一頁"):
        reader.run("1150910-14")


def test_empty_linked_work_orders(monkeypatch):
    reader, _ = _reader(monkeypatch, [_table([])])
    result = reader.run("1150910-14")
    assert result["count"] == 0
    assert result["records"] == []


def test_merged_notice_keeps_the_work_order_table_notice(monkeypatch):
    reader, _ = _reader(
        monkeypatch,
        [_table(
            ["115-2A-69254-001", "115-C1-36682"],
            row_notice="1150915-58", row_status="併單",
        )],
    )
    result = reader.run("1150917-41")
    assert result["fault_notice"] == "1150917-41"
    assert result["count"] == 2
    assert [row["工作單"] for row in result["records"]] == [
        "115-2A-69254-001", "115-C1-36682"
    ]
    assert all(row["通報號"] == "1150915-58" for row in result["records"])
    assert all(row["狀態"] == "併單" for row in result["records"])


@pytest.mark.skipif(not RECORDED_DOM.is_file(), reason="local recording unavailable")
def test_recorded_dom_has_three_expected_work_orders():
    html = RECORDED_DOM.read_text(encoding="utf-8")
    schema, rows = parse_maximo_table(html, required_headers=FIELDS, table_summary="檢視所有段檢修工單")
    assert schema is not None
    page = parse_maximo_page_info(html, table_prefix=schema.prefix, context_name="關聯工單")
    assert (page.start, page.end, page.total) == (1, 3, 3)
    assert [row["工作單"] for row in rows] == ["115-C1-35820", "115-C2-35988", "115-1A-70151"]
    assert all(row["通報號"] == "1150910-14" for row in rows)
