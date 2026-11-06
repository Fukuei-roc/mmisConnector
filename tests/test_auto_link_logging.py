import json
import logging

from mmis_connector.auto_link.orchestrator import AutoLinkUnprocessedFaultNotices
from mmis_connector.auto_link.store import AutoLinkStore
from mmis_connector.run_logging import command_log
from mmis_connector import run_logging


COMMAND = "auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders"
LOGGER_NAME = "mmis_connector.auto_link"


class Runner:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, *args):
        self.calls.append(args)
        return self.result


def _run(tmp_path, source_record, query_result, link_result):
    source = Runner({
        "success": True,
        "query_name": "本段未處理通報",
        "count": 1,
        "records": [source_record],
    })
    query = Runner(query_result)
    linker = Runner(link_result)
    with command_log(COMMAND, LOGGER_NAME):
        with AutoLinkStore(tmp_path / "state.sqlite3") as store:
            result = AutoLinkUnprocessedFaultNotices(
                object(),
                store,
                source_query_factory=lambda _: source,
                work_order_query_factory=lambda _: query,
                linker_factory=lambda _: linker,
            ).run()
    files = list((tmp_path / "logs").glob("*/*/*.jsonl"))
    assert len(files) == 1
    events = [
        json.loads(line)
        for line in files[0].read_text(encoding="utf-8").splitlines()
    ]
    return result, events, query, linker, files[0]


def test_no_match_log_captures_exact_query_and_empty_result_without_source_detail(
    tmp_path, monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_logging, "PROJECT_ROOT", tmp_path)
    source_record = {
        "通報號": "1151104-51",
        "車組/車號": "EP731",
        "發生日期": "2026/11/04",
        "故障現象": "secret fault symptom",
    }
    result, events, query, linker, path = _run(
        tmp_path, source_record,
        {"success": True, "count": 0, "records": []},
        {"success": True, "linked": True},
    )

    assert result["no_matching_work_order"] == 1
    assert query.calls == [("731", ">2026/11/04")]
    assert linker.calls == []
    started = next(e for e in events if e["event"] == "work_order_query_started")
    assert started["run_id"] == result["run_id"]
    assert started["fault_notice_no"] == "1151104-51"
    assert started["source_index"] == 1
    assert started["vehicle"] == "731"
    assert started["date_condition"] == ">2026/11/04"
    assert started["depot"] == "新竹機務段"
    assert started["work_order_status_filter"] == "執行中已派工,核簽中"
    completed = next(e for e in events if e["event"] == "work_order_query_completed")
    assert completed["count"] == 0
    assert completed["candidates"] == []
    assert next(e for e in events if e["event"] == "work_order_selection")["status"] == "no_matching_work_order"
    assert "secret fault symptom" not in path.read_text(encoding="utf-8")
    assert logging.getLogger(LOGGER_NAME).handlers == []


def test_link_log_records_safe_candidate_and_outcome(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_logging, "PROJECT_ROOT", tmp_path)
    source_record = {
        "通報號": "1151104-51",
        "車組/車號": "EP731",
        "發生日期": "2026/11/04",
        "故障現象": "secret fault symptom",
    }
    work_order = {
        "工作單": "115-1A-81570",
        "檢修日期": "2026/11/06",
        "車組/車號": "EMU731",
        "工作單狀態": "執行中已派工",
        "故障現象": "secret response detail",
    }
    result, events, _, linker, path = _run(
        tmp_path, source_record,
        {"success": True, "count": 1, "records": [work_order]},
        {"success": True, "linked": True, "token": "secret token"},
    )

    assert result["linked"] == 1
    assert linker.calls == [("115-1A-81570", "1151104-51")]
    completed = next(e for e in events if e["event"] == "work_order_query_completed")
    assert completed["candidates"] == [{
        "work_order_no": "115-1A-81570",
        "inspection_date": "2026/11/06",
        "vehicle": "EMU731",
        "status": "執行中已派工",
    }]
    assert next(e for e in events if e["event"] == "link_succeeded")["work_order_no"] == "115-1A-81570"
    assert next(e for e in events if e["event"] == "run_completed")["completed"] is True
    log_text = path.read_text(encoding="utf-8")
    assert "secret" not in log_text
    assert logging.getLogger(LOGGER_NAME).handlers == []


def test_log_path_stays_under_project_when_called_from_another_directory(
    tmp_path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(run_logging, "PROJECT_ROOT", project)
    monkeypatch.chdir(elsewhere)

    with command_log(COMMAND, LOGGER_NAME) as logger:
        run_logging.log_event(logger, "check")

    files = list((project / "logs").glob("*/*/*.jsonl"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8"))["event"] == "check"
    assert not (elsewhere / "logs").exists()


def test_log_write_failure_warns_once_without_sensitive_details(
    tmp_path, monkeypatch, capsys,
) -> None:
    class BrokenStream:
        def write(self, _line):
            raise OSError("secret disk detail")

        def flush(self):
            pass

    monkeypatch.setattr(run_logging, "PROJECT_ROOT", tmp_path)
    with command_log(COMMAND, LOGGER_NAME) as logger:
        handler = logger.handlers[0]
        stream = handler.stream
        handler.stream = BrokenStream()
        try:
            run_logging.log_event(logger, "check", detail="secret payload")
            run_logging.log_event(logger, "check", detail="secret payload")
        finally:
            handler.stream = stream

    warning = capsys.readouterr().err
    assert warning.count("紀錄可能不完整") == 1
    assert "secret" not in warning
