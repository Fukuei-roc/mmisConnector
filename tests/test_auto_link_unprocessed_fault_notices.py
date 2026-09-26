from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from mmis_connector.auth import MMISClientError
from mmis_connector.auto_link_store import AutoLinkStore
from mmis_connector.auto_link_unprocessed_fault_notices_to_daily_inspection_work_orders import (
    AutoLinkUnprocessedFaultNotices,
    normalize_auto_link_vehicle,
    select_earliest_work_order,
)


def _source(notice: str, vehicle: str = "717") -> dict[str, str]:
    return {
        "通報號": notice,
        "車組/車號": vehicle,
        "發生日期": "2026/09/23",
    }


def _order(number: str, date: str) -> dict[str, str]:
    return {"工作單": number, "檢修日期": date}


class FakeRunner:
    def __init__(self, callback: Callable[..., dict[str, Any]]) -> None:
        self.callback = callback
        self.calls: list[tuple[str, ...]] = []

    def run(self, *args: str) -> dict[str, Any]:
        self.calls.append(args)
        return self.callback(*args)


def _factory(runner: FakeRunner, seen_clients: list[object]):
    def build(client):
        seen_clients.append(client)
        return runner

    return build


def _source_result(records: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "success": True,
        "query_name": "本段未處理通報(車輛配屬段)",
        "count": len(records),
        "records": records,
    }


@pytest.mark.parametrize(
    ("source_vehicle", "query_vehicle"),
    [
        ("EP9393", "939"),
        ("EM9393", "939"),
        ("EP9503", "950"),
        ("ED9501", "950"),
        ("EM9422", "942"),
        ("EMU946", "946"),
        ("EMC722", "722"),
        ("ED883", "883"),
        ("EP884", "884"),
        ("717", "717"),
    ],
)
def test_normalizes_source_vehicle_for_daily_inspection_query(
    source_vehicle: str, query_vehicle: str
) -> None:
    assert normalize_auto_link_vehicle(source_vehicle) == query_vehicle


def test_rejects_source_vehicle_without_digits() -> None:
    with pytest.raises(MMISClientError, match="數字"):
        normalize_auto_link_vehicle("EMU")


def test_batch_queries_normalized_vehicle_but_preserves_source_value(
    tmp_path,
) -> None:
    source = FakeRunner(
        lambda: _source_result([_source("1150925-01", "EP9393")])
    )

    def query(vehicle: str, date: str) -> dict[str, Any]:
        assert vehicle == "939"
        assert date == ">2026/09/23"
        return {"success": True, "count": 0, "records": []}

    work_orders = FakeRunner(query)
    linker = FakeRunner(lambda *_: {"success": True, "linked": True})

    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        result = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()
        stored = store.connection.execute(
            "SELECT vehicle FROM fault_notices WHERE run_id = ?",
            (result["run_id"],),
        ).fetchone()

        assert result["no_matching_work_order"] == 1
        assert work_orders.calls == [("939", ">2026/09/23")]
        assert linker.calls == []
        assert stored["vehicle"] == "EP9393"


def test_selects_earliest_strictly_later_unique_work_order() -> None:
    selection = select_earliest_work_order(
        [
            _order("WO-SAME-DAY", "2026/09/23"),
            _order("WO-LATE", "2026/09/25"),
            _order("WO-EARLY", "2026/09/24"),
            _order("WO-EARLY", "2026/09/24"),
        ],
        "2026/09/23",
    )

    assert selection.status == "work_order_selected"
    assert selection.work_order_no == "WO-EARLY"


def test_refuses_different_work_orders_on_same_earliest_date() -> None:
    selection = select_earliest_work_order(
        [
            _order("WO-1", "2026/09/24"),
            _order("WO-2", "2026/09/24"),
            _order("WO-3", "2026/09/25"),
        ],
        "2026/09/23",
    )

    assert selection.status == "ambiguous_work_order"
    assert selection.work_order_no is None


def test_batch_reuses_client_links_one_and_accepts_no_result(tmp_path) -> None:
    client = object()
    seen_clients: list[object] = []
    source = FakeRunner(
        lambda: _source_result([_source("1150923-01", "717"), _source("1150923-02", "718")])
    )

    def query(vehicle: str, date: str) -> dict[str, Any]:
        assert date == ">2026/09/23"
        records = (
            [_order("115-1A-71002", "2026/09/24")]
            if vehicle == "717"
            else []
        )
        return {"success": True, "count": len(records), "records": records}

    work_orders = FakeRunner(query)
    linker = FakeRunner(lambda *_: {"success": True, "linked": True})

    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        result = AutoLinkUnprocessedFaultNotices(
            client,
            store,
            source_query_factory=_factory(source, seen_clients),
            work_order_query_factory=_factory(work_orders, seen_clients),
            linker_factory=_factory(linker, seen_clients),
        ).run()

        assert seen_clients == [client, client, client]
        assert linker.calls == [("115-1A-71002", "1150923-01")]
        assert result["linked"] == 1
        assert result["no_matching_work_order"] == 1
        assert result["completed"] is True


def test_ambiguous_result_is_recorded_without_linking(tmp_path) -> None:
    source = FakeRunner(lambda: _source_result([_source("1150923-01")]))
    work_orders = FakeRunner(
        lambda *_: {
            "success": True,
            "count": 2,
            "records": [
                _order("115-1A-1", "2026/09/24"),
                _order("115-1A-2", "2026/09/24"),
            ],
        }
    )
    linker = FakeRunner(lambda *_: {"success": True, "linked": True})

    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        result = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()

        assert result["ambiguous_work_order"] == 1
        assert result["completed"] is True
        assert linker.calls == []


def test_invalid_source_is_terminal_and_does_not_query(tmp_path) -> None:
    source = FakeRunner(lambda: _source_result([_source("", vehicle="")]))
    work_orders = FakeRunner(lambda *_: {"success": True, "count": 0, "records": []})
    linker = FakeRunner(lambda *_: {"success": True, "linked": True})

    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        result = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()

        assert result["invalid_source_data"] == 1
        assert work_orders.calls == []
        assert linker.calls == []


def test_query_failure_is_retryable_on_next_invocation(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    source = FakeRunner(lambda: _source_result([_source("1150923-01")]))
    attempts = 0

    def query(*_: str) -> dict[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise MMISClientError("暫時查詢失敗")
        return {
            "success": True,
            "count": 1,
            "records": [_order("115-1A-1", "2026/09/24")],
        }

    work_orders = FakeRunner(query)
    linker = FakeRunner(lambda *_: {"success": True, "linked": True})

    with AutoLinkStore(database) as store:
        first = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()
        assert first["query_failed"] == 1
        assert first["completed"] is False

    with AutoLinkStore(database) as store:
        second = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()
        assert second["resumed"] is True
        assert second["linked"] == 1
        assert source.calls == [()]


def test_link_error_is_recorded_and_never_retried(tmp_path) -> None:
    database = tmp_path / "state.sqlite3"
    source = FakeRunner(lambda: _source_result([_source("1150923-01")]))
    work_orders = FakeRunner(
        lambda *_: {
            "success": True,
            "count": 1,
            "records": [_order("115-1A-1", "2026/09/24")],
        }
    )
    linker = FakeRunner(
        lambda *_: (_ for _ in ()).throw(MMISClientError("勾稽結果不明"))
    )

    with AutoLinkStore(database) as store:
        first = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()
        assert first["link_error"] == 1
        assert first["manual_review_required"] == 1
        assert first["completed"] is False

    with AutoLinkStore(database) as store:
        second = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()
        assert second["resumed"] is True
        assert second["link_error"] == 1
        assert len(linker.calls) == 1
        assert len(work_orders.calls) == 1
        assert len(source.calls) == 1


def test_unexpected_link_exception_is_redacted(tmp_path) -> None:
    source = FakeRunner(lambda: _source_result([_source("1150923-01")]))
    work_orders = FakeRunner(
        lambda *_: {
            "success": True,
            "count": 1,
            "records": [_order("115-1A-1", "2026/09/24")],
        }
    )
    linker = FakeRunner(
        lambda *_: (_ for _ in ()).throw(RuntimeError("secret=response-body"))
    )

    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        result = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()
        run_id = result["run_id"]
        row = store.connection.execute(
            "SELECT result_message FROM fault_notices WHERE run_id = ?", (run_id,)
        ).fetchone()
        assert "secret" not in row["result_message"]
        assert "人工確認" in row["result_message"]


def test_unconfirmed_link_result_is_a_non_retryable_error(tmp_path) -> None:
    source = FakeRunner(lambda: _source_result([_source("1150923-01")]))
    work_orders = FakeRunner(
        lambda *_: {
            "success": True,
            "count": 1,
            "records": [_order("115-1A-1", "2026/09/24")],
        }
    )
    linker = FakeRunner(lambda *_: {"success": False, "linked": False})

    with AutoLinkStore(tmp_path / "state.sqlite3") as store:
        result = AutoLinkUnprocessedFaultNotices(
            object(),
            store,
            source_query_factory=lambda _: source,
            work_order_query_factory=lambda _: work_orders,
            linker_factory=lambda _: linker,
        ).run()

        assert result["linked"] == 0
        assert result["link_error"] == 1
        assert result["completed"] is False
