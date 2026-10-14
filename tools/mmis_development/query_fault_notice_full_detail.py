from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.analysis_materials import collect_analysis_materials
from mmis_connector.fault_notices.full_detail import FaultNoticeFullDetailReader
from mmis_connector.fault_notices.reader import normalize_fault_notice

from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.query_fault_notice_full_detail <通報號>"


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    notice = normalize_fault_notice(args[0])
    client = MMISSession(MMISConfig.from_env())
    client.login()
    result = FaultNoticeFullDetailReader(client).run(notice)
    result["故障分析素材"] = collect_analysis_materials(client, result["段修工單"])
    return result


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
