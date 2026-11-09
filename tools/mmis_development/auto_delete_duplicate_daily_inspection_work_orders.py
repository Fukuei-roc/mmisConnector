"""Find and cancel duplicate unassigned 1A work orders."""
from __future__ import annotations

import sqlite3
import sys
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.cancel import DailyInspectionWorkOrderCanceller
from mmis_connector.daily_inspection.unassigned import FIELDS, UnassignedDailyInspectionWorkOrderQuery
from mmis_connector.daily_inspection.reader import (
    DailyInspectionWorkOrderDetailReader,
    parse_daily_inspection_basic_info,
)

DATABASE_RELATIVE_PATH = Path("data/auto_delete_duplicate_daily_inspection_work_orders.db")
DATABASE_PATH = Path(__file__).resolve().parents[2] / DATABASE_RELATIVE_PATH
TABLE = "daily_inspection_work_orders"
PENDING_CANCELLATION = "待工單取消"
CANCELLED = "已取消工單"
NO_DUPLICATE = "無重複"
OPENING_DATE_FORMAT = "%Y/%m/%d %H:%M"


@dataclass(frozen=True)
class DuplicateUpdateResult:
    duplicate_groups: int
    dates_written: int
    cancellation_orders: tuple[str, ...]
    incomplete_groups: tuple[str, ...]
    ambiguous_groups: tuple[str, ...]


def replace_records(records: list[dict[str, str]], path: Path = DATABASE_PATH) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    queried_at = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f'DROP TABLE IF EXISTS {TABLE}')
        connection.execute(f'''CREATE TABLE {TABLE} (
            "車組/車號" TEXT NOT NULL,
            "工作單" TEXT NOT NULL PRIMARY KEY,
            "預計檢修(進廠)日" TEXT NOT NULL,
            "查詢時間" TEXT NOT NULL,
            "開單日期" TEXT NOT NULL DEFAULT '',
            "執行結果" TEXT NOT NULL
        )''')
        connection.executemany(
            f'INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?, ?)',
            ((record[FIELDS[0]], record[FIELDS[1]], record[FIELDS[2]], queried_at, "", "")
             for record in records),
        )
        count = connection.execute(f'SELECT COUNT(*) FROM {TABLE}').fetchone()[0]
        if count != len(records):
            raise MMISClientError("未派工日檢工單寫入筆數不符")
        return count


def query_opening_date(client: MMISSession, work_order: str) -> dict[str, str]:
    _, detail = DailyInspectionWorkOrderDetailReader(client).open_detail(work_order)
    return parse_daily_inspection_basic_info(detail, expected_work_order=work_order)


def update_duplicate_work_orders(
    path: Path,
    read_detail: Callable[[str], dict[str, str]],
) -> DuplicateUpdateResult:
    with closing(sqlite3.connect(path)) as connection:
        snapshot_rows = connection.execute(
            f'''SELECT "車組/車號", "工作單", "預計檢修(進廠)日", "查詢時間"
                FROM {TABLE}
                WHERE TRIM("車組/車號") <> ''
                ORDER BY "車組/車號", "工作單"'''
        ).fetchall()
        snapshot_version = connection.execute("PRAGMA data_version").fetchone()[0]

        groups: dict[str, list[str]] = {}
        for vehicle, work_order, _, _ in snapshot_rows:
            groups.setdefault(vehicle, []).append(work_order)
        duplicates = {
            vehicle: work_orders
            for vehicle, work_orders in groups.items()
            if len(work_orders) > 1
        }

        dates: dict[str, str] = {}
        cancellations: list[str] = []
        incomplete: list[str] = []
        ambiguous: list[str] = []
        for vehicle, work_orders in duplicates.items():
            group_dates: dict[str, datetime] = {}
            group_failed = False
            for work_order in work_orders:
                try:
                    detail = read_detail(work_order)
                    if detail.get("工作單") != work_order or detail.get("車組/車號") != vehicle:
                        raise MMISClientError("日檢工單明細與快照工作單或車組/車號不符")
                    opening_date = detail.get("開單日期", "").strip()
                    parsed_date = datetime.strptime(opening_date, OPENING_DATE_FORMAT)
                except (MMISClientError, ValueError) as exc:
                    group_failed = True
                    print(
                        f"Warning: could not verify opening date for {vehicle} {work_order} "
                        f"({type(exc).__name__})",
                        file=sys.stderr,
                    )
                    continue
                dates[work_order] = opening_date
                group_dates[work_order] = parsed_date

            if group_failed:
                incomplete.append(vehicle)
                continue
            latest_date = max(group_dates.values())
            latest_orders = [order for order, date in group_dates.items() if date == latest_date]
            if len(latest_orders) != 1:
                ambiguous.append(vehicle)
                print(
                    f"Warning: opening-date tie for {vehicle}; no cancellation status written",
                    file=sys.stderr,
                )
                continue
            latest_order = latest_orders[0]
            cancellations.extend(order for order in work_orders if order != latest_order)

        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("PRAGMA data_version").fetchone()[0] != snapshot_version:
            raise MMISClientError("SQLite 快照在明細查詢期間已更新，取消本次補寫")
        current_snapshot = connection.execute(
            f'''SELECT "車組/車號", "工作單", "預計檢修(進廠)日", "查詢時間"
                FROM {TABLE}
                WHERE TRIM("車組/車號") <> ''
                ORDER BY "車組/車號", "工作單"'''
        ).fetchall()
        if current_snapshot != snapshot_rows:
            raise MMISClientError("SQLite 快照在明細查詢期間已更新，取消本次補寫")
        connection.executemany(
            f'UPDATE {TABLE} SET "執行結果" = ? WHERE "工作單" = ?',
            ((NO_DUPLICATE, work_orders[0]) for work_orders in groups.values()
             if len(work_orders) == 1),
        )
        for vehicle in duplicates:
            connection.execute(
                f'''UPDATE {TABLE} SET "開單日期" = '', "執行結果" = ''
                    WHERE "車組/車號" = ?''',
                (vehicle,),
            )
        connection.executemany(
            f'UPDATE {TABLE} SET "開單日期" = ? WHERE "工作單" = ?',
            ((opening_date, work_order) for work_order, opening_date in dates.items()),
        )
        connection.executemany(
            f'UPDATE {TABLE} SET "執行結果" = ? WHERE "工作單" = ?',
            ((PENDING_CANCELLATION, work_order) for work_order in cancellations),
        )
        connection.commit()
    return DuplicateUpdateResult(
        duplicate_groups=len(duplicates),
        dates_written=len(dates),
        cancellation_orders=tuple(cancellations),
        incomplete_groups=tuple(incomplete),
        ambiguous_groups=tuple(ambiguous),
    )


def cancel_pending_work_orders(
    path: Path,
    cancel: Callable[[str], dict[str, object]],
) -> tuple[str, ...]:
    with closing(sqlite3.connect(path)) as connection:
        work_orders = [row[0] for row in connection.execute(
            f'SELECT "工作單" FROM {TABLE} WHERE "執行結果" = ? ORDER BY rowid',
            (PENDING_CANCELLATION,),
        )]
        cancelled: list[str] = []
        for work_order in work_orders:
            try:
                result = cancel(work_order)
            except MMISClientError as exc:
                raise MMISClientError(
                    f"工單 {work_order} 取消失敗或結果不明，請人工確認；程式未繼續處理"
                ) from exc
            if (result.get("success") is not True
                    or result.get("工作單") != work_order
                    or result.get("工作單狀態") != "工單取消"):
                raise MMISClientError(f"工單 {work_order} 取消結果未通過確認，請人工確認")
            with connection:
                updated = connection.execute(
                    f'UPDATE {TABLE} SET "執行結果" = ? '
                    'WHERE "工作單" = ? AND "執行結果" = ?',
                    (CANCELLED, work_order, PENDING_CANCELLATION),
                ).rowcount
                if updated != 1:
                    raise MMISClientError(f"工單 {work_order} 的 SQLite 狀態已變更，請人工確認")
            cancelled.append(work_order)
        return tuple(cancelled)


def main(argv: list[str] | None = None) -> int:
    if (sys.argv[1:] if argv is None else argv):
        print("Error: this command accepts no arguments", file=sys.stderr)
        return 2
    try:
        client = MMISSession(MMISConfig.from_env())
        records = UnassignedDailyInspectionWorkOrderQuery(client).run()
        count = replace_records(records)
        result = update_duplicate_work_orders(
            DATABASE_PATH,
            lambda work_order: query_opening_date(client, work_order),
        )
        cancelled = cancel_pending_work_orders(
            DATABASE_PATH,
            DailyInspectionWorkOrderCanceller(client).run,
        )
    except MMISClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"Records found: {count}")
    print(f"Duplicate vehicle groups: {result.duplicate_groups}")
    print(f"Opening dates queried: {result.dates_written}")
    print(f"Cancellation candidates: {len(result.cancellation_orders)}")
    print(f"Work orders cancelled: {len(cancelled)}")
    if result.duplicate_groups == 0:
        print("未發現重複的未派工日檢工單")
    else:
        vehicles_by_order = {record["工作單"]: record["車組/車號"] for record in records}
        for work_order in cancelled:
            print(f"已刪除的車組/車號：{vehicles_by_order[work_order]}，工作單：{work_order}")
    print(f"Incomplete vehicle groups: {len(result.incomplete_groups)}")
    print(f"Ambiguous vehicle groups: {len(result.ambiguous_groups)}")
    print(f"Database path: {DATABASE_RELATIVE_PATH.as_posix()}")
    return int(bool(result.incomplete_groups or result.ambiguous_groups))


if __name__ == "__main__":
    raise SystemExit(main())
