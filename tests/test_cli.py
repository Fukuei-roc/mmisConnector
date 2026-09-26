import json

from mmis_connector import cli


def test_missing_command_returns_json_error_without_running_handler(
    capsys,
) -> None:
    exit_code = cli.main([])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["success"] is False
    assert cli.QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND in result["message"]


def test_unknown_command_returns_json_error(capsys) -> None:
    exit_code = cli.main(["unknown-command"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["error"] == "MMISClientError"


def test_valid_command_dispatches_to_registered_handler(monkeypatch, capsys) -> None:
    expected = {"success": True, "query_name": "test", "count": 0, "records": []}
    monkeypatch.setattr(
        cli,
        "_commands",
        lambda: {
            cli.QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND: lambda args: expected
        },
    )
    exit_code = cli.main([cli.QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == expected


def test_daily_inspection_command_forwards_two_parameters(
    monkeypatch, capsys
) -> None:
    expected = {"success": True, "count": 0, "records": []}
    received = []

    def handler(args):
        received.extend(args)
        return expected

    monkeypatch.setattr(
        cli,
        "_commands",
        lambda: {
            (
                cli.QUERY_DAILY_INSPECTION_WORK_ORDERS_BY_VEHICLE_AND_DATE_COMMAND
            ): handler
        },
    )

    exit_code = cli.main(
        [
            cli.QUERY_DAILY_INSPECTION_WORK_ORDERS_BY_VEHICLE_AND_DATE_COMMAND,
            "703",
            ">2026/09/22",
        ]
    )

    assert exit_code == 0
    assert received == ["703", ">2026/09/22"]
    assert json.loads(capsys.readouterr().out) == expected


def test_daily_inspection_command_requires_two_parameters(capsys) -> None:
    exit_code = cli.main(
        [
            cli.QUERY_DAILY_INSPECTION_WORK_ORDERS_BY_VEHICLE_AND_DATE_COMMAND,
            "703",
        ]
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["error"] == "MMISClientError"
    assert "<車組/車號> <檢修日期條件" in result["message"]


def test_daily_inspection_detail_command_forwards_work_order(
    monkeypatch, capsys
) -> None:
    expected = {"success": True, "count": 0, "records": []}
    received = []

    def handler(args):
        received.extend(args)
        return expected

    monkeypatch.setattr(
        cli,
        "_commands",
        lambda: {
            cli.QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_COMMAND: handler
        },
    )

    exit_code = cli.main(
        [
            cli.QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_COMMAND,
            "115-1A-70048",
        ]
    )

    assert exit_code == 0
    assert received == ["115-1A-70048"]
    assert json.loads(capsys.readouterr().out) == expected


def test_daily_inspection_detail_command_requires_one_parameter(capsys) -> None:
    exit_code = cli.main(
        [cli.QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_COMMAND]
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["error"] == "MMISClientError"
    assert "<工作單號>" in result["message"]


def test_fault_notice_link_command_forwards_two_parameters(
    monkeypatch, capsys
) -> None:
    expected = {"success": True, "linked": True, "returned_to_list": True}
    received = []

    def handler(args):
        received.extend(args)
        return expected

    monkeypatch.setattr(
        cli,
        "_commands",
        lambda: {
            (
                cli.QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_AND_LINK_FAULT_NOTICE_COMMAND
            ): handler
        },
    )

    exit_code = cli.main(
        [
            cli.QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_AND_LINK_FAULT_NOTICE_COMMAND,
            "115-1A-71002",
            "1150923-36",
        ]
    )

    assert exit_code == 0
    assert received == ["115-1A-71002", "1150923-36"]
    assert json.loads(capsys.readouterr().out) == expected


def test_fault_notice_link_command_requires_two_parameters(capsys) -> None:
    exit_code = cli.main(
        [
            cli.QUERY_DAILY_INSPECTION_WORK_ORDER_BY_NUMBER_AND_LINK_FAULT_NOTICE_COMMAND,
            "115-1A-71002",
        ]
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["error"] == "MMISClientError"
    assert "<工作單號> <故障通報號>" in result["message"]


def test_auto_link_command_runs_orchestrator_with_one_client_and_store(
    monkeypatch, capsys
) -> None:
    expected = {
        "success": True,
        "operation_name": "自動勾稽日檢未處理通報",
        "total": 2,
        "linked": 1,
        "failed": 1,
    }
    config = object()
    client = object()
    received = {}

    class FakeStore:
        def __enter__(self):
            received["store"] = self
            return self

        def __exit__(self, *_):
            received["store_closed"] = True

    class FakeOrchestrator:
        def __init__(self, actual_client, actual_store):
            received["client"] = actual_client
            received["orchestrator_store"] = actual_store

        def run(self):
            return expected

    monkeypatch.setattr(cli.MMISConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "MMISSession", lambda actual: client)
    monkeypatch.setattr(cli, "AutoLinkStore", FakeStore)
    monkeypatch.setattr(
        cli, "AutoLinkUnprocessedFaultNotices", FakeOrchestrator
    )

    exit_code = cli.main([cli.AUTO_LINK_UNPROCESSED_FAULT_NOTICES_COMMAND])

    assert exit_code == 0
    assert received == {
        "store": received["store"],
        "client": client,
        "orchestrator_store": received["store"],
        "store_closed": True,
    }
    assert json.loads(capsys.readouterr().out) == expected


def test_auto_link_command_rejects_parameters_before_loading_config(
    monkeypatch, capsys
) -> None:
    def unexpected_config_load():
        raise AssertionError("config should not load for invalid arguments")

    monkeypatch.setattr(cli.MMISConfig, "from_env", unexpected_config_load)

    exit_code = cli.main(
        [cli.AUTO_LINK_UNPROCESSED_FAULT_NOTICES_COMMAND, "unexpected"]
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["error"] == "MMISClientError"
    assert result["message"] == (
        f"用法: {cli.AUTO_LINK_UNPROCESSED_FAULT_NOTICES_COMMAND}"
    )
