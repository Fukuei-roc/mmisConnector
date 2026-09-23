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
        lambda: {cli.QUERY_DAILY_INSPECTION_WORK_ORDERS_COMMAND: handler},
    )

    exit_code = cli.main(
        [cli.QUERY_DAILY_INSPECTION_WORK_ORDERS_COMMAND, "703", "2026/09/22"]
    )

    assert exit_code == 0
    assert received == ["703", "2026/09/22"]
    assert json.loads(capsys.readouterr().out) == expected


def test_daily_inspection_command_requires_two_parameters(capsys) -> None:
    exit_code = cli.main(
        [cli.QUERY_DAILY_INSPECTION_WORK_ORDERS_COMMAND, "703"]
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["error"] == "MMISClientError"
    assert "<車組/車號> <檢修日期 YYYY/MM/DD>" in result["message"]
