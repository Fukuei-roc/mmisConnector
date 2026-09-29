import json

import pytest

from mmis_connector import cli


DEVELOPMENT_ONLY_COMMANDS = (
    "query-unprocessed-fault-notices",
    "query-daily-inspection-work-orders-by-vehicle-and-date",
    "query-daily-inspection-work-order-by-number",
    "query-daily-inspection-work-order-by-number-and-link-fault-notice",
)


def test_production_cli_only_registers_auto_link() -> None:
    assert set(cli._commands()) == {
        cli.AUTO_LINK_UNPROCESSED_FAULT_NOTICES_COMMAND
    }


def test_missing_command_only_advertises_production_command(capsys) -> None:
    exit_code = cli.main([])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert cli.AUTO_LINK_UNPROCESSED_FAULT_NOTICES_COMMAND in result["message"]
    assert all(
        command not in result["message"]
        for command in DEVELOPMENT_ONLY_COMMANDS
    )


@pytest.mark.parametrize("command", DEVELOPMENT_ONLY_COMMANDS)
def test_production_cli_rejects_development_only_commands(command, capsys) -> None:
    exit_code = cli.main([command])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["error"] == "MMISClientError"
    assert command not in cli._commands()


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
