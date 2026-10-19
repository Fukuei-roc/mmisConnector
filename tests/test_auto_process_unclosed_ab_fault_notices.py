from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from mmis_connector.auth import MMISClientError
from mmis_connector.fault_notices.query import (
    UNCLOSED_DEPOT_NAME, UNCLOSED_INCIDENT_LEVELS, UNCLOSED_QUERY_NAME,
)
from tools.mmis_development import auto_process_unclosed_ab_fault_notices as tool


def notice(number: str = "1150910-14", *, atp: bool | None = True) -> dict:
    return {
        "車次": "123", "車組/車號": "EMU900", "發生日期": "2026/09/10",
        "事故等級": "A", "ATP故障": atp, "故障現象": "原始現象",
        "狀態": "測試狀態", "通報號": number,
    }


def query_result(*records: dict) -> dict:
    return {
        "success": True, "query_name": UNCLOSED_QUERY_NAME,
        "filters": {"配屬段別名稱": UNCLOSED_DEPOT_NAME,
                    "事故等級": UNCLOSED_INCIDENT_LEVELS},
        "count": len(records), "records": list(records),
    }


def run(monkeypatch, path: Path, result: dict) -> dict:
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices", lambda: result)
    return tool.execute([], database_path=path)


def read_rows(path: Path) -> list[sqlite3.Row]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            "SELECT * FROM unclosed_ab_fault_notices ORDER BY \"通報號\""
        ).fetchall()


def test_success_schema_summary_and_reserved_nulls(monkeypatch, tmp_path) -> None:
    path = tmp_path / "data" / "notices.db"
    source = notice()
    source.update({field: 1 for field in tool.RESERVED_FIELDS[:-1]})
    source["備註"] = "原始備註"
    result = run(monkeypatch, path, query_result(source))

    assert result == {
        "success": True, "status": "success",
        "database": "data/unclosed_ab_fault_notices.db",
        "table": "unclosed_ab_fault_notices", "records_fetched": 1,
        "records_saved": 1, "sync_mode": "full_replace",
    }
    rows = read_rows(path)
    assert len(rows) == 1
    assert tuple(rows[0].keys()) == (*tool.BASIC_FIELDS, *tool.RESERVED_FIELDS)
    assert rows[0]["ATP故障"] == 1
    assert rows[0]["故障現象"] == "原始現象"
    assert all(rows[0][field] is None for field in tool.RESERVED_FIELDS)
    with sqlite3.connect(path) as connection:
        columns = connection.execute("PRAGMA table_info(unclosed_ab_fault_notices)").fetchall()
    assert [(row[1], row[2], row[3], row[5]) for row in columns] == list(tool.COLUMNS)


@pytest.mark.parametrize("atp,expected", [(True, 1), (False, 0), (None, None)])
def test_atp_boolean_values(monkeypatch, tmp_path, atp, expected) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice(atp=atp)))
    assert read_rows(path)[0]["ATP故障"] == expected


def test_full_replace_resets_reserved_columns(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice(), notice("1150911-03")))
    with sqlite3.connect(path) as connection:
        connection.execute('''UPDATE unclosed_ab_fault_notices
            SET "Fault Analysis Completed" = 1, "備註" = "人工確認"
            WHERE "通報號" = "1150910-14"''')
    second = notice()
    second["事故等級"] = "B"
    result = run(monkeypatch, path, query_result(second, notice("1150915-02")))
    rows = read_rows(path)
    assert result["records_saved"] == 2
    assert [row["通報號"] for row in rows] == ["1150910-14", "1150915-02"]
    assert rows[0]["事故等級"] == "B"
    assert all(row[field] is None for row in rows for field in tool.RESERVED_FIELDS)


def test_empty_success_clears_old_rows(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    assert run(monkeypatch, path, query_result())["records_saved"] == 0
    assert read_rows(path) == []


@pytest.mark.parametrize("change", [
    lambda value: value.update(success=False),
    lambda value: value.update(count=2),
    lambda value: value.update(records="invalid"),
    lambda value: value.update(query_name="其他查詢"),
    lambda value: value.update(filters={"事故等級": "C"}),
    lambda value: value["records"][0].update({"事故等級": "C"}),
    lambda value: value["records"][0].pop("通報號"),
    lambda value: value["records"][0].update({"通報號": ""}),
    lambda value: value["records"][0].update({"ATP故障": "true"}),
    lambda value: value["records"][0].update({"狀態": ""}),
])
def test_invalid_or_incomplete_result_preserves_old_data(
    monkeypatch, tmp_path, change
) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    invalid = query_result(notice("1150911-03"))
    change(invalid)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices", lambda: invalid)
    with pytest.raises(MMISClientError):
        tool.execute([], database_path=path)
    assert [row["通報號"] for row in read_rows(path)] == ["1150910-14"]


def test_duplicate_number_rejected_before_write(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    duplicate = notice("1150911-03")
    conflict = {**duplicate, "故障現象": "不同內容"}
    with pytest.raises(MMISClientError, match="重複"):
        run(monkeypatch, path, query_result(duplicate, conflict))
    assert [row["通報號"] for row in read_rows(path)] == ["1150910-14"]


def test_database_failure_rolls_back_old_rows(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    with sqlite3.connect(path) as connection:
        connection.execute('''CREATE TRIGGER reject_new BEFORE INSERT
            ON unclosed_ab_fault_notices BEGIN SELECT RAISE(FAIL, 'test'); END''')
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("1150911-03")))
    state = tool.SyncState()
    with pytest.raises(sqlite3.IntegrityError):
        tool.execute([], database_path=path, state=state)
    assert state.transaction_started and state.rolled_back and state.old_data_unchanged
    assert [row["通報號"] for row in read_rows(path)] == ["1150910-14"]


def test_wrong_existing_schema_is_not_replaced(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE unclosed_ab_fault_notices ("通報號" TEXT)')
        connection.execute('INSERT INTO unclosed_ab_fault_notices VALUES ("old")')
    with pytest.raises(MMISClientError, match="schema"):
        run(monkeypatch, path, query_result(notice()))
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            'SELECT "通報號" FROM unclosed_ab_fault_notices'
        ).fetchall() == [("old",)]


def test_existing_trigger_cannot_fill_reserved_columns(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    with sqlite3.connect(path) as connection:
        connection.execute('''CREATE TRIGGER fill_reserved AFTER INSERT
            ON unclosed_ab_fault_notices BEGIN
            UPDATE unclosed_ab_fault_notices SET "備註" = 'filled'
            WHERE "通報號" = NEW."通報號"; END''')
    state = tool.SyncState()
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("1150911-03")))
    with pytest.raises(MMISClientError, match="預留欄位"):
        tool.execute([], database_path=path, state=state)
    assert state.rolled_back
    assert [row["通報號"] for row in read_rows(path)] == ["1150910-14"]


def test_query_failure_json_and_no_transaction(monkeypatch, tmp_path, capsys) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    monkeypatch.setattr(tool, "DATABASE_PATH", path)

    def fail():
        raise MMISClientError("查詢失敗")

    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices", fail)
    assert tool.main([]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["success"] is False
    assert summary["transaction_started"] is False
    assert summary["rolled_back"] is False
    assert summary["old_data_unchanged"] is True
    assert [row["通報號"] for row in read_rows(path)] == ["1150910-14"]


def test_database_failure_json_reports_rollback(monkeypatch, tmp_path, capsys) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    with sqlite3.connect(path) as connection:
        connection.execute('''CREATE TRIGGER reject_new BEFORE INSERT
            ON unclosed_ab_fault_notices BEGIN SELECT RAISE(FAIL, 'test'); END''')
    monkeypatch.setattr(tool, "DATABASE_PATH", path)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("1150911-03")))
    assert tool.main([]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["transaction_started"] is True
    assert summary["rolled_back"] is True
    assert summary["old_data_unchanged"] is True
    assert "test" not in summary["message"]


def test_default_database_path_ignores_current_directory(monkeypatch, tmp_path) -> None:
    path = tmp_path / "project" / "data" / "unclosed_ab_fault_notices.db"
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    monkeypatch.setattr(tool, "DATABASE_PATH", path)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice()))
    assert tool.execute([])["records_saved"] == 1
    assert [row["通報號"] for row in read_rows(path)] == ["1150910-14"]
    assert not (other_cwd / "data").exists()


def test_fixed_database_path_and_read_only_query_reuse(monkeypatch) -> None:
    assert tool.DATABASE_PATH == Path(__file__).resolve().parents[1] / (
        "data/unclosed_ab_fault_notices.db")
    calls = []

    class FakeSession:
        def __init__(self, config):
            calls.append("session")

        def login(self):
            calls.append("login")

    class FakeQuery:
        def __init__(self, client):
            assert isinstance(client, FakeSession)
            calls.append("query")

        def run(self):
            calls.append("run")
            return query_result()

    monkeypatch.setattr(tool.MMISConfig, "from_env", lambda: object())
    monkeypatch.setattr(tool, "MMISSession", FakeSession)
    monkeypatch.setattr(tool, "UnclosedFaultNoticeQuery", FakeQuery)
    assert tool.fetch_unclosed_fault_notices() == query_result()
    assert calls == ["session", "login", "query", "run"]
    assert "query_fault_notice_full_detail" not in tool.__dict__
    assert "openai" not in tool.__dict__
