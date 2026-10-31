"""Export unique work orders currently awaiting the configured group leader."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mmis_connector.auth import MMISConfig, MMISSession
from mmis_connector.daily_inspection.reader import DailyInspectionInspectionRecordReader
from mmis_connector.temporary_repair.reader import TemporaryRepairProcedureReader

from . import _unclosed_ab_xlsx as xlsx


APPROVER_ENV_NAME = "MMIS_INSPECTION_GROUP_LEADER"
SHEET_NAME = "優先簽核工單"
FILE_PREFIX = "優先簽核工單_程式產生"


def pending_numbers(rows: list[tuple[Any, ...]], columns: tuple[str, ...]) -> list[str]:
    index = columns.index("待簽核工單")
    numbers: dict[str, None] = {}
    for row in rows:
        if row[index] is None:
            continue
        try:
            values = json.loads(row[index])
        except (TypeError, ValueError) as exc:
            raise xlsx.XlsxExportError("SQLite 待簽核工單不是有效的 JSON 陣列") from exc
        if not isinstance(values, list) or any(
            not isinstance(number, str) or not number.strip() for number in values
        ):
            raise xlsx.XlsxExportError("SQLite 待簽核工單不是非空字串陣列")
        numbers.update((number.strip(), None) for number in values)
    return list(numbers)


def export_priority_xlsx(
    database_path: Path, table_name: str, columns: tuple[str, ...], *,
    output_directory: Path | None = None, now: datetime | None = None,
) -> dict[str, Any]:
    load_dotenv(xlsx.ROOT / ".env", override=False)
    approver = os.getenv(APPROVER_ENV_NAME, "").strip()
    if not approver:
        raise xlsx.XlsxExportError(f"未設定 {APPROVER_ENV_NAME}；請在專案 .env 設定檢查組長姓名")
    directory = output_directory if output_directory is not None else xlsx.configured_output_directory()
    if not directory.is_dir():
        raise xlsx.XlsxExportError("XLSX 輸出資料夾不存在")
    numbers = pending_numbers(xlsx.read_snapshot(database_path, table_name, columns), columns)
    selected: list[tuple[str]] = []
    client = MMISSession(MMISConfig.from_env()) if numbers else None
    for number in numbers:
        if re.fullmatch(r"\d+-C\d+-\d+(?:-\d+)*", number):
            result = TemporaryRepairProcedureReader(client).run(number)
            daily = False
        elif re.fullmatch(r"\d+-1A-\d+", number):
            result = DailyInspectionInspectionRecordReader(client).run(number)
            daily = True
        else:
            raise xlsx.XlsxExportError(f"優先簽核不支援的待簽核工單類型: {number}")
        if (not isinstance(result, dict) or result.get("success") is not True
                or result.get("工作單") != number):
            raise xlsx.XlsxExportError(f"優先簽核查詢未成功或工單號不符: {number}")
        people = result.get("待簽核人")
        if not isinstance(people, list) or any(not isinstance(person, str) for person in people):
            raise xlsx.XlsxExportError(f"優先簽核查詢缺少有效的待簽核人清單: {number}")
        if daily and not isinstance(result.get("檢修段"), str):
            raise xlsx.XlsxExportError(f"日檢工單查詢缺少檢修段: {number}")
        if approver in people and (not daily or result["檢修段"] == "新竹機務段"):
            selected.append((number,))
    workbook = xlsx.build_workbook(
        selected, ("工作單號",), frozenset(), row_height=15.5,
        vertical_alignment="top", column_widths={"工作單號": 36.1},
    )
    workbook.active.title = SHEET_NAME
    return xlsx.save_workbook(
        workbook, directory, file_prefix=FILE_PREFIX,
        records_exported=len(selected), columns_exported=1, now=now,
    )
