from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mmis_connector.overdue_work_orders import FIELDS, OverdueWorkOrderQuery
from tools.mmis_development.audit_overdue_work_orders import replace_records


DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings\2026-11-05_query-overdue-work-orders"
    r"\dom\2026-11-05T015548-891.html"
)


def synthetic_page(order: str, position: int, *, next_page: bool) -> str:
    headers = "".join(
        f'<span id="orders_ttrow_[C:{index}]_ttitle-lb">{field}</span>'
        for index, field in enumerate(FIELDS, start=1)
    )
    cells = "".join(
        f'<td id="orders_tdrow_[C:{index}]-c[R:0]">'
        f'{order if field == "工單編號" else field}</td>'
        for index, field in enumerate(FIELDS, start=1)
    )
    button = "on" if next_page else "off"
    return (
        headers
        + f'<div id="orders_tbod_tdrow-tr[R:0]">{cells}</div>'
        + f'<label id="orders-lb3" class="tCount">{position} - {position}/2</label>'
        + f'<a id="orders-ti7"><img id="orders-ti7_img" '
        + f'src="tablebtn_next_{button}.gif"></a>'
    )


def test_query_reads_every_page_without_recording() -> None:
    query = OverdueWorkOrderQuery.__new__(OverdueWorkOrderQuery)

    class Events:
        def load_app_with_response(self, **kwargs):
            assert kwargs["app_value"] == "ZZ_WO_OVERDUE"
            return object(), synthetic_page("WO-1", 1, next_page=True)

        def post(self, **kwargs):
            assert kwargs["target_id"] == "orders-ti7"
            return synthetic_page("WO-2", 2, next_page=False)

    query.events = Events()
    query.client = type("Client", (), {"state": None})()
    assert [row["工單編號"] for row in query.run()] == ["WO-1", "WO-2"]


def test_recorded_page_yields_all_eight_columns() -> None:
    if not DOM.exists():
        pytest.skip("local recording is unavailable")
    html = DOM.read_text(encoding="utf-8")
    query = OverdueWorkOrderQuery.__new__(OverdueWorkOrderQuery)

    class Events:
        def load_app_with_response(self, **kwargs):
            assert kwargs["app_value"] == "ZZ_WO_OVERDUE"
            return object(), html

    query.events = Events()
    query.client = type("Client", (), {"state": None})()
    records = query.run()
    assert len(records) == 10
    assert all(tuple(record) == FIELDS for record in records)
    assert records[0]["工單編號"]


def test_replacement_clears_old_rows_and_notes(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    first = {field: "x" for field in FIELDS}
    first["工單編號"] = "WO-1"
    second = {field: "y" for field in FIELDS}
    second["工單編號"] = "WO-2"
    replace_records([first], path)
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE overdue_work_orders SET "備註" = ?', ("edited",))
    assert replace_records([second], path) == 1
    with sqlite3.connect(path) as connection:
        columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(overdue_work_orders)"))
        rows = connection.execute('SELECT "工單編號", "備註" FROM overdue_work_orders').fetchall()
    assert columns == (*FIELDS, "備註")
    assert rows == [("WO-2", "")]


def test_failed_replacement_rolls_back_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "overdue.db"
    old = {field: "old" for field in FIELDS}
    old["工單編號"] = "WO-OLD"
    replace_records([old], path)
    broken = dict(old)
    broken.pop("逾期天數")
    with pytest.raises(KeyError):
        replace_records([broken], path)
    with sqlite3.connect(path) as connection:
        rows = connection.execute('SELECT "工單編號" FROM overdue_work_orders').fetchall()
    assert rows == [("WO-OLD",)]
