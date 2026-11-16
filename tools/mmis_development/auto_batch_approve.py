from __future__ import annotations

import json
from collections.abc import Sequence

from mmis_connector.auth import MMISClientError, MMISConfig, MMISSession
from mmis_connector.batch_approval import approve_all_pending, query_pending_counts

from ._support import run_json_tool


USAGE = "python -m tools.mmis_development.auto_batch_approve"


def _print_report(report: dict[str, object]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


def execute(args: Sequence[str]) -> dict[str, object]:
    if args:
        raise MMISClientError(f"用法: {USAGE}")
    config = MMISConfig.from_env(credential_prefix="MMIS_DEPUTY")
    if config.username != "0776044":
        raise MMISClientError("MMIS_DEPUTY_USERNAME 必須是指定的副段長帳號")
    client = MMISSession(config)
    client.login()
    initial = query_pending_counts(client)
    _print_report({"核簽前待簽數量": initial})

    approved = approve_all_pending(client)
    approved_nonzero = {
        category: count for category, count in approved.items() if count > 0
    }
    _print_report({"本次已簽核數量": approved_nonzero})

    final = query_pending_counts(client)
    all_zero = not any(final.values())
    report = {"最後待簽數量": final, "全部為零": all_zero}
    if not all_zero:
        _print_report(report)
        raise MMISClientError("最後複查仍有待簽工單")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    return run_json_tool(execute, argv)


if __name__ == "__main__":
    raise SystemExit(main())
