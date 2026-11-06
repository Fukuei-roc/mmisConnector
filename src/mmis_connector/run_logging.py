"""Per-invocation JSON Lines logs for production commands."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from typing import Iterator
from uuid import uuid4


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
    directory = Path("logs") / command / now.strftime("%Y-%m-%d")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex}.jsonl"
    handler = logging.FileHandler(path, encoding="utf-8")
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
