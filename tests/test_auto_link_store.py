from __future__ import annotations

import sqlite3

import pytest

from mmis_connector.auto_link.store import (
    AutoLinkStore, LINK_INTERRUPTED_MESSAGE, SOURCE_FIELDS,
)


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
                "SELECT processing_status FROM auto_link_state"
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
            "SELECT COUNT(*) FROM fault_notices"
        ).fetchone()[0] == 0
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
                FROM auto_link_state WHERE id = ?
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


def test_result_view_reports_source_time_and_confirmed_links(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        AutoLinkStore, "_now", staticmethod(lambda: "2026-10-22T17:34:56+00:00")
    )
    database = tmp_path / "state.sqlite3"
    statuses = (
        "pending",
        "work_order_selected",
        "linking",
        "link_error",
        "linked",
        "no_matching_work_order",
    )
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(
            prepared.run_id,
            "測試查詢",
            [_record(f"1150923-{index:02d}") for index in range(len(statuses))],
        )
        rows = store.list_processable(prepared.run_id)
        for row, status in zip(rows, statuses):
            if status != "pending":
                store.set_status(
                    prepared.run_id,
                    row["id"],
                    status,
                    work_order_no="115-1A-71002",
                )

    with sqlite3.connect(database) as observer:
        columns = [
            row[1] for row in observer.execute("PRAGMA table_info('自動勾稽結果')")
        ]
        result = observer.execute(
            'SELECT * FROM "自動勾稽結果" ORDER BY "通報號"'
        ).fetchall()

    assert columns == [
        "查詢時間", "車次", "車組/車號", "發生日期", "事故等級",
        "ATP故障", "故障現象", "狀態", "通報號", "已關聯的工單",
        "執行結果",
    ]
    assert result[0] == (
        "2026-10-23T01:34:56+08:00", "1234", "EMU717", "2026/09/23",
        "C", "false", "測試", "立案", "1150923-00", None, "未執行",
    )
    assert [row[-2:] for row in result] == [
        (None, "未執行"),
        (None, "未執行"),
        (None, "否"),
        (None, "否"),
        ("115-1A-71002", "是"),
        (None, "未找到對應日檢工單"),
    ]
    with sqlite3.connect(database) as observer:
        assert observer.execute(
            'SELECT * FROM fault_notices ORDER BY "通報號"'
        ).fetchall() == result


def test_fault_notices_is_the_eleven_column_physical_table(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])

    with sqlite3.connect(database) as observer:
        assert observer.execute(
            "SELECT type FROM sqlite_master WHERE name = 'fault_notices'"
        ).fetchone()[0] == "table"
        assert [row[1] for row in observer.execute(
            "PRAGMA table_info(fault_notices)"
        )] == [
            "查詢時間", "車次", "車組/車號", "發生日期", "事故等級",
            "ATP故障", "故障現象", "狀態", "通報號", "已關聯的工單",
            "執行結果",
        ]
        assert observer.execute(
            'SELECT "通報號", "執行結果" FROM fault_notices'
        ).fetchone() == ("1150923-36", "未執行")


def _legacy_database(database) -> None:
    columns = ", ".join(f"{column} TEXT" for _, column in SOURCE_FIELDS)
    with sqlite3.connect(database) as connection:
        connection.execute("""
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY, status TEXT, source_loaded INTEGER,
                started_at TEXT, completed_at TEXT, source_query_name TEXT
            )
        """)
        connection.execute(f"""
            CREATE TABLE fault_notices (
                id INTEGER PRIMARY KEY, run_id TEXT, source_index INTEGER,
                {columns}, source_record_json TEXT,
                daily_inspection_work_order_no TEXT, processing_status TEXT,
                result_message TEXT, attempt_count INTEGER,
                created_at TEXT, updated_at TEXT
            )
        """)
        connection.execute("""
            INSERT INTO runs VALUES ('old', 'running', 1,
                '2026-10-22T17:34:56+00:00', NULL, '測試查詢')
        """)
        connection.execute("""
            INSERT INTO fault_notices (
                id, run_id, source_index, train_no, vehicle,
                occurrence_date, incident_level, atp_fault,
                fault_symptom, source_status, fault_notice_no,
                source_record_json, daily_inspection_work_order_no,
                processing_status, result_message, attempt_count,
                created_at, updated_at
            ) VALUES (7, 'old', 1, '1234', 'EMU717', '2026/09/23',
                'C', 'false', '測試', '立案', '1150923-36', '{}',
                '115-1A-71002', 'linked', NULL, 1,
                '2026-10-22T17:34:56+00:00', '2026-10-22T17:34:56+00:00')
        """)
        connection.execute('CREATE VIEW "自動勾稽結果" AS SELECT * FROM fault_notices')


def test_legacy_database_migrates_preserving_state_and_result(tmp_path) -> None:
    database = tmp_path / "legacy.sqlite3"
    _legacy_database(database)

    with AutoLinkStore(database) as store:
        row = store.get_row("old", 7)
        assert row["processing_status"] == "linked"
        assert row["daily_inspection_work_order_no"] == "115-1A-71002"
        assert store.prepare_run().resumed is True
        assert store.connection.execute('''
            SELECT "查詢時間", "已關聯的工單", "執行結果"
            FROM fault_notices
        ''').fetchone()[:] == (
            "2026-10-23T01:34:56+08:00", "115-1A-71002", "是"
        )

    with AutoLinkStore(database) as reopened:
        assert reopened.get_row("old", 7)["processing_status"] == "linked"
        assert reopened.connection.execute(
            'SELECT COUNT(*) FROM fault_notices'
        ).fetchone()[0] == 1


def test_reopening_migrated_database_does_not_rewrite_result_rows(tmp_path) -> None:
    database = tmp_path / "legacy.sqlite3"
    _legacy_database(database)
    with AutoLinkStore(database):
        pass

    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE result_writes (operation TEXT)")
        connection.execute('''
            CREATE TRIGGER audit_result_delete AFTER DELETE ON fault_notices BEGIN
                INSERT INTO result_writes VALUES ('delete');
            END
        ''')
        connection.execute('''
            CREATE TRIGGER audit_result_insert AFTER INSERT ON fault_notices BEGIN
                INSERT INTO result_writes VALUES ('insert');
            END
        ''')

    with AutoLinkStore(database) as reopened:
        assert reopened.connection.execute(
            'SELECT "通報號" FROM fault_notices'
        ).fetchone()[0] == "1150923-36"
        assert reopened.connection.execute(
            "SELECT COUNT(*) FROM result_writes"
        ).fetchone()[0] == 0


def test_failed_migration_keeps_original_table(tmp_path) -> None:
    database = tmp_path / "broken.sqlite3"
    _legacy_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE fault_notices DROP COLUMN train_no")

    with pytest.raises(sqlite3.OperationalError):
        AutoLinkStore(database)

    with sqlite3.connect(database) as observer:
        assert observer.execute(
            "SELECT COUNT(*) FROM fault_notices"
        ).fetchone()[0] == 1
        assert observer.execute(
            "SELECT name FROM sqlite_master WHERE name = 'auto_link_state'"
        ).fetchone() is None


def test_status_updates_sync_physical_result_with_state(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(prepared.run_id)[0]["id"]

        store.set_status(
            prepared.run_id, row_id, "work_order_selected",
            work_order_no="115-1A-71002",
        )
        assert store.connection.execute(
            'SELECT "已關聯的工單", "執行結果" FROM fault_notices'
        ).fetchone()[:] == (None, "未執行")

        store.set_status(prepared.run_id, row_id, "linking")
        assert store.connection.execute(
            'SELECT "已關聯的工單", "執行結果" FROM fault_notices'
        ).fetchone()[:] == (None, "否")

        store.set_status(prepared.run_id, row_id, "linked")

    with sqlite3.connect(database) as observer:
        assert observer.execute(
            'SELECT "已關聯的工單", "執行結果" FROM fault_notices'
        ).fetchone() == ("115-1A-71002", "是")


def test_result_insert_failure_rolls_back_state_update(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(prepared.run_id)[0]["id"]
        store.set_status(
            prepared.run_id, row_id, "work_order_selected",
            work_order_no="115-1A-71002",
        )
        store.connection.execute('''
            CREATE TRIGGER reject_linked_result BEFORE INSERT ON fault_notices
            WHEN NEW."執行結果" = '是' BEGIN
                SELECT RAISE(FAIL, 'result insert rejected');
            END
        ''')

        with pytest.raises(sqlite3.IntegrityError, match="result insert rejected"):
            store.set_status(prepared.run_id, row_id, "linked")

        assert store.get_row(prepared.run_id, row_id)["processing_status"] == (
            "work_order_selected"
        )
        assert store.connection.execute(
            'SELECT "已關聯的工單", "執行結果" FROM fault_notices'
        ).fetchone()[:] == (None, "未執行")


def test_existing_database_gains_result_view_without_changing_rows(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        store.connection.execute('DROP VIEW "自動勾稽結果"')
        store.connection.commit()

    with AutoLinkStore(database) as reopened:
        original = reopened.connection.execute(
            'SELECT "查詢時間", "通報號" FROM "自動勾稽結果"'
        ).fetchone()
        assert original[1] == "1150923-36"
        assert reopened.prepare_run().resumed is True
        assert reopened.connection.execute(
            'SELECT "查詢時間", "通報號" FROM "自動勾稽結果"'
        ).fetchone() == original
        with pytest.raises(sqlite3.OperationalError):
            reopened.connection.execute(
                'UPDATE "自動勾稽結果" SET "通報號" = "changed"'
            )


def test_existing_result_table_renames_column_and_marks_missing_order(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(prepared.run_id)[0]["id"]
        store.set_status(prepared.run_id, row_id, "no_matching_work_order")
        before = store.get_row(prepared.run_id, row_id)

    with AutoLinkStore(database) as reopened:
        assert reopened.get_row(prepared.run_id, row_id) == before
        assert [row[1] for row in reopened.connection.execute(
            "PRAGMA table_info(fault_notices)"
        )][-1] == "執行結果"
        assert reopened.connection.execute(
            'SELECT "執行結果" FROM fault_notices'
        ).fetchone()[0] == "未找到對應日檢工單"
        assert reopened.connection.execute(
            'SELECT "執行結果" FROM "自動勾稽結果"'
        ).fetchone()[0] == "未找到對應日檢工單"


def _old_result_database(database) -> tuple[str, int]:
    with AutoLinkStore(database) as store:
        prepared = store.prepare_run()
        store.import_source_records(prepared.run_id, "測試查詢", [_record()])
        row_id = store.list_processable(prepared.run_id)[0]["id"]
        store.set_status(prepared.run_id, row_id, "no_matching_work_order")
    with sqlite3.connect(database) as connection:
        connection.execute(
            'ALTER TABLE fault_notices RENAME COLUMN "執行結果" TO "關聯執行成功"'
        )
        connection.execute(
            'UPDATE fault_notices SET "關聯執行成功" = "未執行"'
        )
        connection.execute("DROP TRIGGER auto_link_result_update")
        connection.execute("""
            CREATE TRIGGER auto_link_result_update AFTER UPDATE ON auto_link_state
            BEGIN SELECT RAISE(FAIL, 'stale result trigger'); END
        """)
    return prepared.run_id, row_id


def test_old_result_schema_migrates_and_refreshes_sync_triggers(tmp_path) -> None:
    database = tmp_path / "old.sqlite3"
    run_id, row_id = _old_result_database(database)

    with AutoLinkStore(database) as store:
        assert [row[1] for row in store.connection.execute(
            "PRAGMA table_info(fault_notices)"
        )][-1] == "執行結果"
        assert [row[1] for row in store.connection.execute(
            "PRAGMA table_info('自動勾稽結果')"
        )][-1] == "執行結果"
        assert store.connection.execute(
            'SELECT "執行結果" FROM fault_notices WHERE rowid = ?', (row_id,)
        ).fetchone()[0] == "未找到對應日檢工單"
        assert store.get_row(run_id, row_id)["processing_status"] == (
            "no_matching_work_order"
        )
        store.set_status(run_id, row_id, "linked", work_order_no="115-1A-71002")
        assert store.connection.execute(
            'SELECT "已關聯的工單", "執行結果" FROM fault_notices'
        ).fetchone()[:] == ("115-1A-71002", "是")

    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE result_writes (operation TEXT)")
        connection.execute("""
            CREATE TRIGGER audit_result_update AFTER UPDATE ON fault_notices
            BEGIN INSERT INTO result_writes VALUES ('update'); END
        """)
    with AutoLinkStore(database) as reopened:
        assert reopened.connection.execute(
            "SELECT COUNT(*) FROM result_writes"
        ).fetchone()[0] == 0


def test_failed_result_schema_migration_rolls_back(tmp_path) -> None:
    database = tmp_path / "old.sqlite3"
    run_id, row_id = _old_result_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("""
            CREATE TRIGGER reject_result_update BEFORE UPDATE ON fault_notices
            BEGIN SELECT RAISE(FAIL, 'migration rejected'); END
        """)

    with pytest.raises(sqlite3.IntegrityError, match="migration rejected"):
        AutoLinkStore(database)

    with sqlite3.connect(database) as observer:
        assert [row[1] for row in observer.execute(
            "PRAGMA table_info(fault_notices)"
        )][-1] == "關聯執行成功"
        assert observer.execute(
            'SELECT "關聯執行成功" FROM fault_notices WHERE rowid = ?',
            (row_id,),
        ).fetchone()[0] == "未執行"
        assert observer.execute(
            "SELECT processing_status FROM auto_link_state WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0] == "no_matching_work_order"
