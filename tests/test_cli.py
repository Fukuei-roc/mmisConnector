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
        lambda: {cli.QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND: lambda: expected},
    )
    exit_code = cli.main([cli.QUERY_UNPROCESSED_FAULT_NOTICES_COMMAND])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == expected
