"""Export the existing unclosed A/B fault notice database without syncing MMIS."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mmis_connector.auth import MMISClientError

from . import auto_process_unclosed_ab_fault_notices as snapshot
from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.export_unclosed_ab_fault_notices_from_db"
COLUMN_WIDTHS = {
    "車次": 6.5,
    "車組/車號": 11.8,
    "發生日期": 14.5,
    "事故等級": 10.6,
    "ATP故障": 10.6,
    "故障現象": 70,
    "狀態": 10.6,
    "通報號": 14.9,
    "備註": 40,
}
STATUS_RULES = {
    (None, 1, 0, 0, 0, 0): "段修工單未處理完成",
    (None, 1, 0, 1, 0, 0): "等候段修工單簽核中",
    (1, 1, 0, 1, 0, 1): "未處理（含ATP故障分析）",
    (None, 0, 0, 1, 0, 0): "未處理",
    (0, 0, 0, 1, 0, 0): "未處理",
    (0, 0, 1, 0, 0, 0): "未處理（段修工單結案）",
    (None, 1, 1, 0, 0, 0): "可結案",
    (0, 0, 0, 0, 0, 0): "未處理",
}
COLUMN_NAMES = tuple(column[0] for column in snapshot.COLUMNS)
STATUS_INDICES = tuple(COLUMN_NAMES.index(name) for name in snapshot.DETAIL_CHECK_FIELDS)
NOTE_INDEX = COLUMN_NAMES.index("備註")


def annotate_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    status = tuple(row[index] for index in STATUS_INDICES)
    for name, value in zip(snapshot.DETAIL_CHECK_FIELDS, status, strict=True):
        if value is not None and (type(value) is not int or value not in (0, 1)):
            raise MMISClientError(f"SQLite 布林欄位 {name} 含有無效值")
    note = STATUS_RULES.get(status)
    if note is None:
        return row
    updated = list(row)
    updated[NOTE_INDEX] = note
    return tuple(updated)


def execute(
    args: Sequence[str], *, database_path: Path | None = None,
    expected_records: int | None = None,
) -> dict[str, Any]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    try:
        from ._unclosed_ab_xlsx import export_xlsx
    except ModuleNotFoundError as exc:
        if exc.name == "openpyxl":
            raise MMISClientError("未安裝 openpyxl，無法匯出 XLSX") from exc
        raise
    path = database_path or snapshot.DATABASE_PATH
    exported = export_xlsx(
        path,
        snapshot.TABLE_NAME,
        COLUMN_NAMES,
        frozenset({"ATP故障", *snapshot.DETAIL_CHECK_FIELDS}),
        excluded_columns=frozenset(snapshot.DETAIL_CHECK_FIELDS),
        row_height=15.5,
        vertical_alignment="top",
        column_widths=COLUMN_WIDTHS,
        sort_columns=("事故等級", "發生日期", "車組/車號"),
        row_transform=annotate_row,
        expected_records=expected_records,
    )
    return {
        "success": True,
        "operation": "export_existing_sqlite_to_xlsx",
        "database": str(path),
        "table": snapshot.TABLE_NAME,
        "xlsx_export": exported,
    }


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
