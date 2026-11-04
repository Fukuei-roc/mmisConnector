import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from mmis_connector.auth import MMISClientError, PageState
from mmis_connector.daily_inspection.unassigned import UnassignedDailyInspectionWorkOrderQuery
from tools.mmis_development.auto_delete_duplicate_daily_inspection_work_orders import replace_records

STATE = PageState("session", 3, "csrf", "zz_pmwo1a", "https://example.test/app")
HEADERS = ("檢修段", "配屬段", "車組/車號", "檢修級別", "工作單", "車次",
           "檢修單位", "工作單狀態", "處理人員", "預計檢修(進廠)日", "檢修日期")


def page(start: int, end: int, total: int, next_page: bool) -> str:
    headers = "".join(
        f'<span id="table_ttrow_[C:{i}]_ttitle-lb">{name}</span>'
        for i, name in enumerate(HEADERS, 1)
    )
    rows = ""
    for number in range(start, end + 1):
        values = {2: "新竹機務段", 3: "EMU700", 5: str(number),
                  8: "執行中未派工", 10: "2026/11/05"}
        cells = "".join(
            f'<td id="table_tdrow_[C:{column}]-c[R:{number-start}]">'
            f'<span>{values.get(column, name)}</span></td>'
            for column, name in enumerate(HEADERS, 1)
        )
        rows += f'<tr id="table_tbod_tdrow-tr[R:{number-start}]">{cells}</tr>'
    control = '<a id="table-ti7"><img id="table-ti7_img" src="tablebtn_next_on.gif"></a>' if next_page else ""
    return headers + f'<label id="table-lb3" class="tCount">{start} - {end}/{total}</label>' + control + rows


def test_query_collects_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    query = UnassignedDailyInspectionWorkOrderQuery(SimpleNamespace(state=STATE))
    monkeypatch.setattr(query.events, "load_app_with_response", lambda **kw: (STATE, page(1, 1, 1, False)))
    calls = []
    responses = iter(["", "", page(1, 30, 31, True), page(31, 31, 31, False)])

    def post(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(query, "_post_event", post)
    rows = query.run()
    assert len(rows) == 31
    assert rows[-1] == {"車組/車號": "EMU700", "工作單": "31", "預計檢修(進廠)日": "2026/11/05"}
    assert [call["value"] for call in calls[:2]] == ["新竹機務段", "執行中未派工"]
    assert calls[-1]["target_id"] == "table-ti7"


def test_snapshot_replaces_old_rows_and_preserves_on_error(tmp_path: Path) -> None:
    db = tmp_path / "snapshot.db"
    row = {"車組/車號": "EMU700", "工作單": "1", "預計檢修(進廠)日": "2026/11/05"}
    assert replace_records([row], db) == 1
    with sqlite3.connect(db) as connection:
        values = connection.execute('SELECT "車組/車號", "工作單", "預計檢修(進廠)日", "查詢時間", "執行結果" FROM daily_inspection_work_orders').fetchone()
    assert values[:3] == ("EMU700", "1", "2026/11/05")
    assert values[3] and values[4] == ""
    with pytest.raises(KeyError):
        replace_records([{}], db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_inspection_work_orders").fetchone()[0] == 1
    assert replace_records([], db) == 0
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_inspection_work_orders").fetchone()[0] == 0
