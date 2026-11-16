import json
from types import SimpleNamespace

from mmis_connector.batch_approval import EXPECTED_CATEGORIES
from tools.mmis_development import auto_batch_approve


def _reports(output: str) -> list[dict[str, object]]:
    decoder = json.JSONDecoder()
    reports = []
    remaining = output.lstrip()
    while remaining:
        report, end = decoder.raw_decode(remaining)
        reports.append(report)
        remaining = remaining[end:].lstrip()
    return reports


def _fake_login(monkeypatch) -> None:
    class FakeConfig:
        @classmethod
        def from_env(cls, *, credential_prefix):
            assert credential_prefix == "MMIS_DEPUTY"
            return SimpleNamespace(username="0776044")

    class FakeSession:
        def __init__(self, config):
            self.config = config

        def login(self):
            return None

    monkeypatch.setattr(auto_batch_approve, "MMISConfig", FakeConfig)
    monkeypatch.setattr(auto_batch_approve, "MMISSession", FakeSession)


def test_cli_reports_before_approved_and_final_counts(monkeypatch, capsys) -> None:
    _fake_login(monkeypatch)
    initial = {name: 0 for name in EXPECTED_CATEGORIES}
    initial["1A工單"] = 2
    final = {name: 0 for name in EXPECTED_CATEGORIES}
    approved = dict(final, **{"1A工單": 2})
    calls = []
    before_approval = []

    def query(client):
        calls.append("query")
        return initial if len(calls) == 1 else final

    def approve(client):
        calls.append("approve")
        before_approval.append(capsys.readouterr().out)
        return approved

    monkeypatch.setattr(auto_batch_approve, "query_pending_counts", query)
    monkeypatch.setattr(auto_batch_approve, "approve_all_pending", approve)

    assert auto_batch_approve.main([]) == 0
    reports = _reports(before_approval[0] + capsys.readouterr().out)
    assert calls == ["query", "approve", "query"]
    assert reports == [
        {"核簽前待簽數量": initial},
        {"本次已簽核數量": {"1A工單": 2}},
        {"最後待簽數量": final, "全部為零": True},
    ]


def test_cli_shows_final_nonzero_counts_and_exits_with_error(monkeypatch, capsys) -> None:
    _fake_login(monkeypatch)
    zero = {name: 0 for name in EXPECTED_CATEGORIES}
    final = dict(zero, **{"定期檢修工單": 1})
    counts = iter((zero, final))
    monkeypatch.setattr(
        auto_batch_approve, "query_pending_counts", lambda client: next(counts)
    )
    monkeypatch.setattr(
        auto_batch_approve, "approve_all_pending", lambda client: zero
    )

    assert auto_batch_approve.main([]) == 1
    reports = _reports(capsys.readouterr().out)
    assert reports[:3] == [
        {"核簽前待簽數量": zero},
        {"本次已簽核數量": {}},
        {"最後待簽數量": final, "全部為零": False},
    ]
    assert reports[3]["success"] is False
    assert "最後複查仍有待簽工單" in reports[3]["message"]
