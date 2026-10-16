"""Export all accessible ATP fault analysis lookup paths as UTF-8 JSON."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.fault_notices.atp_options import ATPOptionsExporter, write_export
from mmis_connector.fault_notices.reader import normalize_fault_notice

from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.export_atp_fault_analysis_options <已勾選ATP故障的通報號>"
OUTPUT = Path(__file__).resolve().parents[2] / "data" / "atp_fault_analysis_options.json"


def execute(args: Sequence[str]) -> dict[str, Any]:
    if len(args) != 1:
        raise MMISClientError(f"用法: {USAGE}")
    notice = normalize_fault_notice(args[0])
    client = MMISSession(MMISConfig.from_env())
    client.login()
    result = ATPOptionsExporter(client).run(notice)
    output = write_export(result, OUTPUT)
    return {"success": result["traversal_status"] == "completed",
            "traversal_status": result["traversal_status"],
            "output": str(output), "statistics": result["statistics"],
            "errors": result["errors"]}


def main(argv: Sequence[str] | None = None) -> int:
    status = 0

    def handler(args: Sequence[str]) -> dict[str, Any]:
        nonlocal status
        result = execute(args)
        status = 0 if result["success"] else 2
        return result

    return run_json_tool(handler, argv) or status


if __name__ == "__main__":
    raise SystemExit(main())
