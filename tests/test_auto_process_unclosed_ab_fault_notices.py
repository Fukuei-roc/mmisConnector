from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
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
    rows = tool.prepare_rows(result)
    saved = tool.replace_rows(rows, path, tool.SyncState())
    return {"records_saved": saved}


def read_rows(path: Path) -> list[sqlite3.Row]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            "SELECT * FROM unclosed_ab_fault_notices ORDER BY \"通報號\""
        ).fetchall()


def read_waiting(path: Path) -> list[tuple[str, str]]:
    with sqlite3.connect(path) as connection:
        return connection.execute(
            'SELECT "通報號", "新增日期" '
            'FROM a_level_fault_notices_awaiting_closure ORDER BY "通報號"'
        ).fetchall()


def test_success_schema_summary_and_reserved_nulls(monkeypatch, tmp_path) -> None:
    path = tmp_path / "data" / "notices.db"
    source = notice()
    source.update({field: 1 for field in tool.RESERVED_FIELDS[:-1]})
    source["備註"] = "原始備註"
    result = run(monkeypatch, path, query_result(source))

    assert result == {"records_saved": 1}
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
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda number, **kwargs: detail_result(number))
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
    assert "openai" not in tool.__dict__


def detail_result(number: str, readiness: bool | None = None) -> dict:
    return {
        "通報號": number,
        "結案狀態檢查": dict(zip(tool.DETAIL_CHECK_FIELDS, (
            readiness, True, False, False, True, False,
        ), strict=True)),
    }


def closable_detail(number: str) -> dict:
    result = detail_result(number)
    result["結案狀態檢查"].update({
        "All Depot Maintenance Work Orders Closed": True,
        "CA Repair Work Orders Not Closed": False,
    })
    return result


def test_detail_query_reuses_python_function_without_cli(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        tool.query_fault_notice_full_detail, "execute",
        lambda args, **kwargs: calls.append((args, kwargs)) or detail_result(args[0]),
    )
    tool.fetch_fault_notice_detail("1150910-14", check_analysis_readiness=False)
    tool.fetch_fault_notice_detail("1150910-14", check_analysis_readiness=True)
    assert calls == [
        (["1150910-14"], {"include_analysis_materials": False}),
        (["1150910-14", "--check-analysis-readiness"], {"include_analysis_materials": True}),
    ]


@pytest.mark.parametrize("failures, waits", [(1, []), (2, [1])])
def test_detail_query_retries_immediately_then_after_one_second(monkeypatch, failures, waits) -> None:
    calls = []
    slept = []
    monkeypatch.setattr(tool.time, "sleep", slept.append)

    def query(args, **kwargs):
        calls.append(args[0])
        if len(calls) <= failures:
            raise MMISClientError("MMIS 網路請求失敗: TimeoutError")
        return detail_result(args[0])

    monkeypatch.setattr(tool.query_fault_notice_full_detail, "execute", query)
    assert tool.fetch_fault_notice_detail("1150910-14", check_analysis_readiness=False) == detail_result("1150910-14")
    assert calls == ["1150910-14"] * (failures + 1)
    assert slept == waits


def test_detail_query_stops_after_third_failure(monkeypatch) -> None:
    calls = []
    slept = []
    monkeypatch.setattr(tool.time, "sleep", slept.append)

    def fail(args, **kwargs):
        calls.append(args[0])
        raise MMISClientError("查詢失敗")

    monkeypatch.setattr(tool.query_fault_notice_full_detail, "execute", fail)
    with pytest.raises(MMISClientError, match="查詢失敗"):
        tool.fetch_fault_notice_detail("1150910-14", check_analysis_readiness=False)
    assert calls == ["1150910-14"] * 3
    assert slept == [1]


@pytest.mark.parametrize("readiness", [None, True, False])
def test_prepare_detail_checks_types(readiness) -> None:
    values = tool.prepare_detail_checks(
        detail_result("1150910-14", readiness), "1150910-14",
        require_readiness=readiness is not None,
    )
    assert values == (
        None if readiness is None else int(readiness), 1, 0, 0, 1, 0,
    )


def test_prepare_detail_checks_rejects_wrong_notice_missing_or_invalid_values() -> None:
    number = "1150910-14"
    with pytest.raises(MMISClientError, match="通報號不符"):
        tool.prepare_detail_checks(detail_result("other"), number, require_readiness=False)
    missing = detail_result(number)
    del missing["結案狀態檢查"]["Fault Analysis Completed"]
    with pytest.raises(MMISClientError, match="缺少"):
        tool.prepare_detail_checks(missing, number, require_readiness=False)
    invalid = detail_result(number)
    invalid["結案狀態檢查"]["Fault Analysis Completed"] = "true"
    with pytest.raises(MMISClientError, match="型別錯誤"):
        tool.prepare_detail_checks(invalid, number, require_readiness=False)
    with pytest.raises(MMISClientError, match="型別錯誤"):
        tool.prepare_detail_checks(detail_result(number), number, require_readiness=True)
    with pytest.raises(MMISClientError, match="型別錯誤"):
        tool.prepare_detail_checks(detail_result(number, True), number, require_readiness=False)


def test_detail_update_changes_only_selected_row(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice(), notice("1150911-03")))
    values = (None, 1, 0, 0, 1, 0)
    state = tool.SyncState(snapshot_saved=True)
    tool.update_detail_checks("1150910-14", values, path, state)
    rows = read_rows(path)
    assert tuple(rows[0][field] for field in tool.DETAIL_CHECK_FIELDS) == values
    assert rows[0]["備註"] is None
    assert all(rows[1][field] is None for field in tool.RESERVED_FIELDS)
    assert state.detail_updated and not state.detail_rolled_back


def test_detail_update_failure_rolls_back_without_losing_snapshot(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice()))
    state = tool.SyncState(snapshot_saved=True)
    with pytest.raises(MMISClientError, match="未更新唯一通報"):
        tool.update_detail_checks("missing", (None, 1, 0, 0, 1, 0), path, state)
    assert state.detail_transaction_started and state.detail_rolled_back
    assert all(read_rows(path)[0][field] is None for field in tool.RESERVED_FIELDS)


def test_workflow_queries_all_remaining_notices_without_ai(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    first = notice("1150911-03")
    second = notice("1150910-14")
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(first, second))
    calls = []

    def fake_detail(number, *, check_analysis_readiness):
        calls.append((number, check_analysis_readiness))
        return detail_result(number)

    monkeypatch.setattr(tool, "fetch_fault_notice_detail", fake_detail)
    summary = tool.execute([], database_path=path)
    assert summary["records_fetched"] == 2
    assert summary["records_loaded"] == 2
    assert summary["records_saved"] == 2
    assert summary["records_skipped_waiting"] == 0
    assert summary["detail_records_processed"] == 2
    assert summary["detail_checks_saved"] == 10
    assert summary["awaiting_closure_added"] == 0
    assert summary["analysis_readiness"] == "not_run"
    assert calls == [("1150911-03", False), ("1150910-14", False)]
    rows = {row["通報號"]: row for row in read_rows(path)}
    assert tuple(rows[first["通報號"]][field] for field in tool.DETAIL_CHECK_FIELDS) == (
        None, 1, 0, 0, 1, 0,
    )
    assert tuple(rows[second["通報號"]][field] for field in tool.DETAIL_CHECK_FIELDS) == (
        None, 1, 0, 0, 1, 0,
    )
    assert rows[first["通報號"]]["備註"] is None


def test_explicit_readiness_flag_updates_all_six(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice()))
    calls = []

    def fake_detail(number, *, check_analysis_readiness):
        calls.append(check_analysis_readiness)
        return detail_result(number, False)

    monkeypatch.setattr(tool, "fetch_fault_notice_detail", fake_detail)
    summary = tool.execute(["--check-analysis-readiness"], database_path=path)
    assert calls == [True]
    assert summary["detail_checks_saved"] == 6
    assert summary["analysis_readiness"] == "completed"
    assert tuple(read_rows(path)[0][field] for field in tool.DETAIL_CHECK_FIELDS) == (
        0, 1, 0, 0, 1, 0,
    )


def test_empty_snapshot_skips_detail_query(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices", lambda: query_result())
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda *args, **kwargs: pytest.fail("no detail query expected"))
    summary = tool.execute([], database_path=path)
    assert summary["records_saved"] == 0
    assert summary["detail_records_processed"] == 0
    assert read_rows(path) == []


def test_detail_failure_keeps_new_snapshot_without_partial_checks(
    monkeypatch, tmp_path, capsys
) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice("old")))
    monkeypatch.setattr(tool, "DATABASE_PATH", path)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("new")))

    def fail_detail(*args, **kwargs):
        raise MMISClientError("完整通報查詢失敗")

    monkeypatch.setattr(tool, "fetch_fault_notice_detail", fail_detail)
    assert tool.main([]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["snapshot_saved"] is True
    assert summary["detail_updated"] is False
    assert summary["old_data_unchanged"] is False
    assert [row["通報號"] for row in read_rows(path)] == ["new"]
    assert all(read_rows(path)[0][field] is None for field in tool.RESERVED_FIELDS)


def test_detail_update_sql_failure_rolls_back_only_checks(
    monkeypatch, tmp_path, capsys
) -> None:
    path = tmp_path / "notice.db"
    run(monkeypatch, path, query_result(notice("old")))
    with sqlite3.connect(path) as connection:
        connection.execute('''CREATE TRIGGER reject_checks BEFORE UPDATE
            ON unclosed_ab_fault_notices BEGIN SELECT RAISE(FAIL, 'test'); END''')
    monkeypatch.setattr(tool, "DATABASE_PATH", path)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("new")))
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda number, **kwargs: detail_result(number))
    assert tool.main([]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["snapshot_saved"] is True
    assert summary["detail_transaction_started"] is True
    assert summary["detail_rolled_back"] is True
    assert summary["detail_updated"] is False
    assert [row["通報號"] for row in read_rows(path)] == ["new"]
    assert all(read_rows(path)[0][field] is None for field in tool.RESERVED_FIELDS)


def test_bad_detail_result_does_not_update_snapshot(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice()))
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda *args, **kwargs: detail_result("wrong"))
    with pytest.raises(MMISClientError, match="通報號不符"):
        tool.execute([], database_path=path)
    assert all(read_rows(path)[0][field] is None for field in tool.RESERVED_FIELDS)


def test_next_run_requeries_notices_that_are_not_waiting(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("first"), notice("second")))
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda number, **kwargs: detail_result(number))
    tool.execute([], database_path=path)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("second"), notice("first")))
    tool.execute([], database_path=path)
    rows = {row["通報號"]: row for row in read_rows(path)}
    assert rows["first"]["Fault Analysis Completed"] == 1
    assert rows["second"]["Fault Analysis Completed"] == 1


def test_eligible_a_notice_moves_to_persistent_waiting_database(monkeypatch, tmp_path) -> None:
    path = tmp_path / "data" / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    b_notice = notice("B-1")
    b_notice["事故等級"] = "B"
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("A-1"), b_notice))
    calls = []

    def fake_detail(number, **kwargs):
        calls.append(number)
        return closable_detail(number)

    monkeypatch.setattr(tool, "fetch_fault_notice_detail", fake_detail)
    summary = tool.execute([], database_path=path)
    assert calls == ["A-1", "B-1"]
    assert summary["awaiting_closure_added"] == 1
    assert summary["awaiting_closure_total"] == 1
    assert summary["records_saved"] == 1
    assert summary["awaiting_closure_database"] == (
        "data/a_level_fault_notices_awaiting_closure.db"
    )
    assert [row["通報號"] for row in read_rows(path)] == ["B-1"]
    waiting = read_waiting(waiting_path)
    assert len(waiting) == 1 and waiting[0][0] == "A-1"
    assert datetime.fromisoformat(waiting[0][1]).utcoffset() == timedelta(hours=8)
    with sqlite3.connect(waiting_path) as connection:
        columns = connection.execute(
            "PRAGMA table_info(a_level_fault_notices_awaiting_closure)"
        ).fetchall()
    assert [(c[1], c[2], c[3], c[5]) for c in columns] == list(tool.WAITING_COLUMNS)


def test_next_run_skips_waiting_notice_and_preserves_added_date(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    source = query_result(notice("A-1"), notice("A-2"))
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices", lambda: source)
    calls = []

    def fake_detail(number, **kwargs):
        calls.append(number)
        return closable_detail(number) if number == "A-1" else detail_result(number)

    monkeypatch.setattr(tool, "fetch_fault_notice_detail", fake_detail)
    first = tool.execute([], database_path=path)
    added_at = read_waiting(waiting_path)[0][1]
    second = tool.execute([], database_path=path)
    assert first["awaiting_closure_added"] == 1
    assert second["records_fetched"] == 2
    assert second["records_skipped_waiting"] == 1
    assert second["records_loaded"] == 1
    assert second["awaiting_closure_added"] == 0
    assert second["awaiting_closure_total"] == 1
    assert calls == ["A-1", "A-2", "A-2"]
    assert [row["通報號"] for row in read_rows(path)] == ["A-2"]
    assert read_waiting(waiting_path) == [("A-1", added_at)]


@pytest.mark.parametrize("field", [
    "Fault Analysis Completed",
    "All Depot Maintenance Work Orders Closed",
    "Depot Maintenance Work Orders Pending Approval",
    "CA Repair Work Orders Not Closed",
    "ATP Fault Analysis Incomplete",
])
def test_each_required_status_must_match(field) -> None:
    values = (None, 1, 1, 0, 0, 0)
    assert tool.is_awaiting_closure("A", values)
    assert not tool.is_awaiting_closure("B", values)
    index = tool.DETAIL_CHECK_FIELDS.index(field)
    changed = list(values)
    changed[index] = 1 - changed[index]
    assert not tool.is_awaiting_closure("A", tuple(changed))


def test_waiting_schema_mismatch_preserves_existing_main_database(
    monkeypatch, tmp_path
) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    run(monkeypatch, path, query_result(notice("old")))
    with sqlite3.connect(waiting_path) as connection:
        connection.execute('CREATE TABLE a_level_fault_notices_awaiting_closure ("通報號" TEXT)')
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("new")))
    with pytest.raises(MMISClientError, match="schema"):
        tool.execute([], database_path=path)
    assert [row["通報號"] for row in read_rows(path)] == ["old"]


def test_move_failure_rolls_back_both_databases(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("A-1")))
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda number, **kwargs: closable_detail(number))
    tool.load_waiting_notice_numbers(waiting_path)
    with sqlite3.connect(waiting_path) as connection:
        connection.execute('''CREATE TRIGGER reject_waiting BEFORE INSERT
            ON a_level_fault_notices_awaiting_closure
            BEGIN SELECT RAISE(FAIL, 'test'); END''')
    state = tool.SyncState()
    with pytest.raises(sqlite3.IntegrityError):
        tool.execute([], database_path=path, state=state)
    assert state.waiting_transaction_started and state.waiting_rolled_back
    assert state.waiting_added == 0
    assert [row["通報號"] for row in read_rows(path)] == ["A-1"]
    assert read_rows(path)[0]["Fault Analysis Completed"] == 1
    assert read_waiting(waiting_path) == []


def test_waiting_wal_mode_rejects_cross_database_move(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    tool.load_waiting_notice_numbers(waiting_path)
    with sqlite3.connect(waiting_path) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("A-1")))
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda number, **kwargs: closable_detail(number))
    with pytest.raises(MMISClientError, match="WAL"):
        tool.execute([], database_path=path)
    assert [row["通報號"] for row in read_rows(path)] == ["A-1"]
    assert read_waiting(waiting_path) == []


def test_detail_failure_after_first_move_reports_partial_progress(
    monkeypatch, tmp_path, capsys
) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    monkeypatch.setattr(tool, "DATABASE_PATH", path)
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("A-1"), notice("A-2")))

    def fake_detail(number, **kwargs):
        if number == "A-2":
            raise MMISClientError("完整通報查詢失敗")
        return closable_detail(number)

    monkeypatch.setattr(tool, "fetch_fault_notice_detail", fake_detail)
    assert tool.main([]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["snapshot_saved"] is True
    assert summary["detail_records_processed"] == 1
    assert summary["awaiting_closure_added"] == 1
    assert [row["通報號"] for row in read_rows(path)] == ["A-2"]
    assert [row[0] for row in read_waiting(waiting_path)] == ["A-1"]


def test_successful_empty_query_does_not_reset_waiting_database(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    with sqlite3.connect(waiting_path) as connection:
        connection.execute(tool.CREATE_WAITING_TABLE_SQL)
        connection.execute(f"PRAGMA user_version = {tool.WAITING_RECHECK_VERSION}")
        connection.execute(
            'INSERT INTO a_level_fault_notices_awaiting_closure VALUES (?, ?)',
            ("A-1", "2026-10-20T10:00:00+08:00"),
        )
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices", lambda: query_result())
    monkeypatch.setattr(tool, "fetch_fault_notice_detail",
                        lambda *args, **kwargs: pytest.fail("no detail expected"))
    summary = tool.execute([], database_path=path)
    assert summary["records_saved"] == 0
    assert summary["awaiting_closure_total"] == 1
    assert read_waiting(waiting_path) == [("A-1", "2026-10-20T10:00:00+08:00")]


def test_legacy_waiting_database_is_rechecked_once_then_preserved(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    with sqlite3.connect(waiting_path) as connection:
        connection.execute(tool.CREATE_WAITING_TABLE_SQL)
        connection.execute(
            'INSERT INTO a_level_fault_notices_awaiting_closure VALUES (?, ?)',
            ("A-1", "2026-10-19T10:00:00+08:00"),
        )
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("A-1"), notice("A-2")))
    calls = []

    def detail(number, **kwargs):
        calls.append(number)
        return closable_detail(number) if number == "A-1" else detail_result(number)

    monkeypatch.setattr(tool, "fetch_fault_notice_detail", detail)
    first = tool.execute([], database_path=path)
    assert first["records_skipped_waiting"] == 0
    assert first["waiting_rechecked"] is True
    assert calls == ["A-1", "A-2"]
    waiting = read_waiting(waiting_path)
    assert waiting[0][0] == "A-1" and waiting[0][1] != "2026-10-19T10:00:00+08:00"
    with sqlite3.connect(waiting_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == tool.WAITING_RECHECK_VERSION
    calls.clear()
    second = tool.execute([], database_path=path)
    assert second["records_skipped_waiting"] == 1
    assert second["waiting_rechecked"] is False
    assert calls == ["A-2"]
    assert read_waiting(waiting_path) == waiting


def test_one_time_recheck_rolls_back_both_databases_on_snapshot_failure(monkeypatch, tmp_path) -> None:
    path = tmp_path / "notice.db"
    waiting_path = path.with_name(tool.WAITING_DATABASE_NAME)
    tool.replace_rows(tool.prepare_rows(query_result(notice("old"))), path, tool.SyncState())
    with sqlite3.connect(waiting_path) as connection:
        connection.execute(tool.CREATE_WAITING_TABLE_SQL)
        connection.execute(
            'INSERT INTO a_level_fault_notices_awaiting_closure VALUES (?, ?)',
            ("A-1", "2026-10-19T10:00:00+08:00"),
        )
    monkeypatch.setattr(tool, "fetch_unclosed_fault_notices",
                        lambda: query_result(notice("new")))
    monkeypatch.setattr(tool, "INSERT_SQL", "INSERT INTO missing_table VALUES (?)")
    with pytest.raises(sqlite3.Error):
        tool.execute([], database_path=path)
    assert [row["通報號"] for row in read_rows(path)] == ["old"]
    assert read_waiting(waiting_path) == [("A-1", "2026-10-19T10:00:00+08:00")]
    with sqlite3.connect(waiting_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
