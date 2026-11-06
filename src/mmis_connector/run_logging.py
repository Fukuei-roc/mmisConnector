"""Per-invocation JSON Lines logs for production commands."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys
from typing import Iterator
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class _CommandFileHandler(logging.FileHandler):
    def __init__(self, path: Path) -> None:
        super().__init__(path, encoding="utf-8")
        self._write_warning_sent = False

    def handleError(self, record: logging.LogRecord) -> None:
        if self._write_warning_sent:
            return
        self._write_warning_sent = True
        try:
            sys.stderr.write("警告：執行 log 寫入失敗，紀錄可能不完整。\n")
        except OSError:
            pass


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    if logger.isEnabledFor(logging.INFO):
        record = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "event": event,
            **fields,
        }
        try:
            line = json.dumps(record, ensure_ascii=False)
        except (TypeError, ValueError):
            line = json.dumps({
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "event": "log_event_rejected",
                "source_event": event,
            })
        logger.info(line)


@contextmanager
def command_log(command: str, logger_name: str) -> Iterator[logging.Logger]:
    now = datetime.now(UTC)
    directory = PROJECT_ROOT / "logs" / command / now.strftime("%Y-%m-%d")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex}.jsonl"
    handler = _CommandFileHandler(path)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger(logger_name)
    previous_level = logger.level
    previous_propagate = logger.propagate
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    try:
        yield logger
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        handler.close()
