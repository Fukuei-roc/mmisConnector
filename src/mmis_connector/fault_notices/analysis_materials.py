"""Collect linked work-order details for fault analysis."""

from __future__ import annotations

import copy
import logging
import re
import time
from collections.abc import Callable
from typing import Any

import requests

from ..auth import MMISClientError, MMISSession
from ..daily_inspection.reader import DailyInspectionInspectionRecordReader
from ..periodic_inspection.reader import PeriodicInspectionWorkOrderDetailReader
from ..temporary_repair.reader import TemporaryRepairProcedureReader


LOGGER = logging.getLogger(__name__)
ORDER_TYPES = {
    "C1": "臨時檢修工單", "C2": "臨時檢修工單", "C3": "臨時檢修工單",
    "1A": "日檢工單", "2A": "定期檢修工單", "3A": "定期檢修工單",
}
FIELDS = {
    "臨時檢修工單": ("工作單", "車組/車號", "故障現象", "原因說明", "備註", "維修程序概況"),
    "日檢工單": ("工作單", "車組/車號", "檢修記錄", "重要事項紀錄"),
    "定期檢修工單": ("工作單", "車組/車號", "維修程序概況", "檢修記錄", "維修情形", "維修情形(詳述)"),
}
NESTED = {"維修程序概況", "檢修記錄", "重要事項紀錄"}
TRANSIENT_HTTP_STATUS = {408, 429, 500, 502, 503, 504}
NETWORK_ERROR_NAMES = {"ConnectionError", "ConnectTimeout", "ReadTimeout", "Timeout", "TimeoutError"}


def classify_work_order(work_order: object) -> str | None:
    if not isinstance(work_order, str) or not re.fullmatch(r"\d{3}-(?:1A|2A|3A|C1|C2|C3)-\d+(?:-\d+)?", work_order):
        return None
    return ORDER_TYPES[work_order.split("-")[1]]


def is_transient_network_error(error: BaseException | dict[str, Any]) -> bool:
    if isinstance(error, dict):
        if error.get("success") is not False:
            return False
        name = error.get("error")
        message = error.get("message", "")
        if name not in {"MMISClientError", *NETWORK_ERROR_NAMES}:
            return False
        if name in NETWORK_ERROR_NAMES:
            return True
        return isinstance(message, str) and _is_network_message(message)
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, (requests.ConnectionError, requests.Timeout, ConnectionError, TimeoutError)):
            return True
        current = current.__cause__ or current.__context__
    return isinstance(error, MMISClientError) and _is_network_message(str(error))


def _is_network_message(message: str) -> bool:
    if message.startswith("MMIS 網路請求失敗:"):
        return message.partition(":")[2].strip() in NETWORK_ERROR_NAMES
    prefix = "MMIS 回傳非預期 HTTP 狀態: "
    if message.startswith(prefix):
        try:
            return int(message[len(prefix):]) in TRANSIENT_HTTP_STATUS
        except ValueError:
            return False
    return False


def _error_message(error: BaseException | dict[str, Any]) -> str:
    if isinstance(error, dict):
        message = error.get("message") or error.get("error")
        return str(message) if message else "工單查詢失敗"
    if isinstance(error, MMISClientError):
        return str(error)
    if isinstance(error, (requests.RequestException, ConnectionError, TimeoutError)):
        return f"網路請求失敗: {type(error).__name__}"
    return "工單查詢發生未預期錯誤"


def query_with_retry(query: Callable[[str], dict[str, Any]], work_order: str) -> dict[str, Any]:
    for attempt in range(1, 4):
        try:
            result = query(work_order)
            if result.get("success") is True:
                return result
            error: BaseException | dict[str, Any] = result
        except Exception as exc:  # noqa: BLE001 - isolate each MMIS work order
            error = exc
        if attempt == 3 or not is_transient_network_error(error):
            raise MMISClientError(_error_message(error)) from (error if isinstance(error, BaseException) else None)
        LOGGER.warning("工單 %s 第 %d 次網路查詢失敗，準備重試: %s", work_order, attempt, _error_message(error))
        if attempt == 2:
            time.sleep(1)
    raise AssertionError("unreachable")


def extract_fields(kind: str, result: dict[str, Any], work_order: str) -> dict[str, Any]:
    if result.get("success") is not True:
        raise MMISClientError(_error_message(result))
    output: dict[str, Any] = {}
    for field in FIELDS[kind]:
        if field == "工作單":
            output[field] = result.get(field) or work_order
        elif field in NESTED:
            output[field] = copy.deepcopy(result.get(field, {"count": 0, "records": []}))
        else:
            output[field] = result.get(field)
    return output


def collect_analysis_materials(client: MMISSession, work_orders: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    materials: dict[str, list[dict[str, Any]]] = {kind: [] for kind in FIELDS}
    readers = {
        "臨時檢修工單": TemporaryRepairProcedureReader(client),
        "日檢工單": DailyInspectionInspectionRecordReader(client),
        "定期檢修工單": PeriodicInspectionWorkOrderDetailReader(client),
    }
    cache: dict[str, dict[str, Any]] = {}
    for row in work_orders:
        number = row.get("工作單") if isinstance(row, dict) else None
        kind = classify_work_order(number)
        if kind is None:
            LOGGER.warning("略過不支援或格式異常的段修工單: %r", number)
            continue
        assert isinstance(number, str)
        if number not in cache:
            try:
                result = query_with_retry(readers[kind].run, number)
                cache[number] = extract_fields(kind, result, number)
            except Exception as exc:  # noqa: BLE001 - preserve full notice and continue
                message = _error_message(exc)
                LOGGER.error("工單 %s 查詢失敗: %s", number, message)
                cache[number] = {"工作單": number, "查詢狀態": "失敗", "錯誤訊息": message}
        materials[kind].append(copy.deepcopy(cache[number]))
    return materials
