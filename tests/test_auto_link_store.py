from __future__ import annotations

import sqlite3

import pytest

from mmis_connector.auto_link_store import AutoLinkStore, LINK_INTERRUPTED_MESSAGE


def _record(notice: str = "1150923-36") -> dict[str, object]:
    return {
        "車次": "1234",
        "車組/車號": "EMU717",
        "發生日期": "2026/09/23",
        "發生時間": "12:34",
        "事故等級": "C",
        "故障地點": "新竹",
        "ATP故障": False,
        "故障現象": "測試",
        "立案人員": "甲",
        "通報人員": "乙",
        "通報單位": "單位",
        "通報股室": "股室",
        "狀態": "立案",
        "通報號": notice,
        "配屬段別": "HC",
        "配屬段別名稱": "新竹機務段",
        "顏色查詢": "",
    }


def test_creates_schema_imports_all_source_fields_and_commits(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row = store.list_processable(prepared.run_id)[0]

        assert prepared.resumed is False
        assert prepared.source_loaded is False
        assert row["fault_notice_no"] == "1150923-36"
        assert row["vehicle"] == "EMU717"
        assert row["occurrence_date"] == "2026/09/23"
        assert '"故障現象": "測試"' in row["source_record_json"]

        with sqlite3.connect(database) as observer:
            assert observer.execute(
                "SELECT processing_status FROM fault_notices"
            ).fetchone()[0] == "pending"


def test_resumes_running_batch_without_reimporting(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        first = store.prepare_run()
        store.import_source_records(first.run_id, "測試查詢", [_record()])

    with AutoLinkStore(database) as reopened:
        resumed = reopened.prepare_run()

        assert resumed.run_id == first.run_id
        assert resumed.resumed is True
        assert resumed.source_loaded is True
        assert len(reopened.list_processable(first.run_id)) == 1


def test_completed_batch_is_cleared_before_new_run(tmp_path) -> None:
    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        first = store.prepare_run()
        store.import_source_records(first.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(first.run_id)[0]["id"]
        store.set_status(first.run_id, row_id, "linked", work_order_no="115-1A-1")
        assert store.complete_if_settled(first.run_id) is True

        second = store.prepare_run()

        assert second.run_id != first.run_id
        assert second.resumed is False
        assert store.summary(second.run_id)["total"] == 0
        assert store.connection.execute(
            "SELECT COUNT(*) FROM runs WHERE run_id = ?", (first.run_id,)
        ).fetchone()[0] == 0


def test_duplicate_notice_rolls_back_entire_import(tmp_path) -> None:
    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        prepared = store.prepare_run()

        with pytest.raises(sqlite3.IntegrityError):
            store.import_source_records(
                prepared.run_id,
                "測試查詢",
                [_record(), _record()],
            )

        assert store.summary(prepared.run_id)["total"] == 0
        run = store.connection.execute(
            "SELECT source_loaded FROM runs WHERE run_id = ?", (prepared.run_id,)
        ).fetchone()
        assert run["source_loaded"] == 0


def test_missing_notice_values_are_preserved_for_later_validation(tmp_path) -> None:
    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        prepared = store.prepare_run()
        first = _record("")
        second = _record("")
        second["車組/車號"] = "EMU718"

        store.import_source_records(prepared.run_id, "測試查詢", [first, second])

        rows = store.list_processable(prepared.run_id)
        assert len(rows) == 2
        assert rows[0]["fault_notice_no"] is None
        assert rows[1]["fault_notice_no"] is None


def test_each_status_update_is_immediately_visible(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(prepared.run_id)[0]["id"]

        store.begin_attempt(prepared.run_id, row_id)
        store.set_status(
            prepared.run_id,
            row_id,
            "work_order_selected",
            work_order_no="115-1A-71002",
        )

        with sqlite3.connect(database) as observer:
            observed = observer.execute(
                """
                SELECT attempt_count, processing_status,
                       daily_inspection_work_order_no
                FROM fault_notices WHERE id = ?
                """,
                (row_id,),
            ).fetchone()
        assert observed == (1, "work_order_selected", "115-1A-71002")


def test_linking_row_becomes_non_retryable_error_on_resume(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(prepared.run_id)[0]["id"]
        store.set_status(prepared.run_id, row_id, "linking")

    with AutoLinkStore(database) as reopened:
        resumed = reopened.prepare_run()
        row = reopened.get_row(resumed.run_id, row_id)

        assert row["processing_status"] == "link_error"
        assert row["result_message"] == LINK_INTERRUPTED_MESSAGE
        assert reopened.list_processable(resumed.run_id) == []


def test_query_failure_keeps_run_unsettled_and_is_retryable(tmp_path) -> None:
    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(prepared.run_id)[0]["id"]
        store.set_status(prepared.run_id, row_id, "query_failed", message="暫時失敗")

        assert store.complete_if_settled(prepared.run_id) is False
        assert store.list_processable(prepared.run_id)[0]["id"] == row_id


def test_execution_lock_rejects_a_concurrent_process(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as first, AutoLinkStore(database) as second:
        with first.execution_lock():
            with pytest.raises(RuntimeError, match="另一個自動勾稽程序"):
                with second.execution_lock():
                    pass

        with second.execution_lock():
            pass


def test_link_error_keeps_batch_open_without_being_retryable(tmp_path) -> None:
    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        prepared = store.prepare_run()
        store.import_source_records(
            prepared.run_id,
            "測試查詢",
            [_record("1150923-01"), _record("1150923-02")],
        )
        rows = store.list_processable(prepared.run_id)
        store.set_status(prepared.run_id, rows[0]["id"], "linked")
        store.set_status(prepared.run_id, rows[1]["id"], "link_error")

        summary = store.summary(prepared.run_id)
        assert summary["total"] == 2
        assert summary["linked"] == 1
        assert summary["link_error"] == 1
        assert store.complete_if_settled(prepared.run_id) is False
        assert store.list_processable(prepared.run_id) == []
