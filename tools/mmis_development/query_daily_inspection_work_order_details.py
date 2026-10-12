from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.daily_inspection.reader import DailyInspectionInspectionRecordReader

from ._support import run_json_tool


USAGE = (
    "python -m "
    "tools.mmis_development.query_daily_inspection_work_order_details "
    "<工作單號>"
)
PERSONNEL_GROUPS = (
    ("檢查室（檢查員）", "檢查室", "檢查員"),
    ("檢查室（技術人員）", "檢查室", "修繕人員"),
    ("檢車室（檢查員）", "檢車室", "檢查員"),
    ("檢車室（技術人員）", "檢車室", "修繕人員"),
)


def group_maintenance_personnel(personnel: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, Any] = {}
    for title, group, role in PERSONNEL_GROUPS:
        records = sorted(
            (
                {"員工代號": row["員工代號"], "姓名": row["姓名"]}
                for row in personnel["records"]
                if row["人員群組"] == group and row["工作角色"] == role
            ),
            key=lambda row: row["姓名"],
        )
        grouped[title] = {"count": len(records), "records": records}
    return grouped


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    client = MMISSession(MMISConfig.from_env())
    result = DailyInspectionInspectionRecordReader(client).run(args[0])
    return {
        "query_name": result["query_name"],
        "query_work_order_number": result["work_order"],
        "success": result["success"],
        "工作單": result["工作單"],
        "車組/車號": result["車組/車號"],
        "檢修日期": result["檢修日期"],
        "車次": result["車次"],
        "工作單狀態": result["工作單狀態"],
        "開單人姓名": result["開單人姓名"],
        "開單日期": result["開單日期"],
        "已勾稽故障通報": result["linked_fault_notices"],
        "檢修記錄": {"count": result["count"], "records": result["records"]},
        "重要事項紀錄": result["important_notes"],
        "檢修人員": group_maintenance_personnel(result["maintenance_personnel"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
