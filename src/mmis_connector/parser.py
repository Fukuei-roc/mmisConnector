from __future__ import annotations

import html
import re
import warnings
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

from .auth import MMISClientError


HEADER_ID_RE = re.compile(
    r"^(?P<prefix>.+)_ttrow_\[C:(?P<column>\d+)\]_ttitle-lb$"
)
ROW_ID_RE_TEMPLATE = r"^{prefix}_tbod_tdrow-tr\[R:(?P<row>\d+)\]$"
OUTPUT_NAME_OVERRIDES = {"ATP故障?": "ATP故障"}
PAGE_COUNT_RE = re.compile(
    r"^(?P<start>\d+)\s*-\s*(?P<end>\d+)\s*/\s*(?P<total>\d+)$"
)
COUNT_ID_RE = re.compile(r"^(?P<prefix>.+)-lb\d+$")


@dataclass(frozen=True)
class FaultNoticePageInfo:
    start: int
    end: int
    total: int
    next_page_target: str | None


def _parse_maximo_markup(response_text: str) -> tuple[str, BeautifulSoup]:
    decoded = html.unescape(response_text)
    # Maximo wraps replacement HTML in XML CDATA. Flatten those sections before
    # handing the document to an HTML parser so table nodes are actual elements.
    decoded = re.sub(
        r"<!\[CDATA\[(.*?)\]\]>",
        lambda match: match.group(1),
        decoded,
        flags=re.DOTALL,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(decoded, "html.parser")
    return decoded, soup


def _cell_value(cell: Tag, *, is_checkbox: bool) -> str | bool:
    if is_checkbox:
        checkbox = cell.find(attrs={"checked": True})
        if checkbox is None:
            checkbox = cell.find("img", attrs={"checked": re.compile("checked|unchecked")})
        return bool(checkbox and checkbox.get("checked") == "checked")
    value_node = cell.find(id=re.compile(r"_ttxt-lb\[R:\d+\]$"))
    if value_node is None:
        return ""
    title = value_node.get("title")
    return str(title).strip() if title else value_node.get_text(" ", strip=True)


def parse_fault_notice_table(response_text: str) -> list[dict[str, Any]]:
    decoded, soup = _parse_maximo_markup(response_text)

    headers: dict[int, str] = {}
    prefix: str | None = None
    for node in soup.find_all(id=HEADER_ID_RE):
        match = HEADER_ID_RE.match(str(node.get("id")))
        if match is None:
            continue
        column = int(match.group("column"))
        label = node.get_text(" ", strip=True).split("[", 1)[0].strip()
        if label and column not in {0, 18}:
            prefix = prefix or match.group("prefix")
            headers[column] = OUTPUT_NAME_OVERRIDES.get(label, label)

    if prefix is None or not headers:
        if "沒有要顯示的列" in decoded:
            return []
        raise MMISClientError("查詢回應找不到故障通報表頭")

    row_re = re.compile(ROW_ID_RE_TEMPLATE.format(prefix=re.escape(prefix)))
    rows: list[dict[str, Any]] = []
    row_nodes: list[tuple[int, Tag]] = []
    for node in soup.find_all(id=row_re):
        match = row_re.match(str(node.get("id")))
        if match:
            row_nodes.append((int(match.group("row")), node))

    for row_number, row_node in sorted(row_nodes, key=lambda item: item[0]):
        record: dict[str, Any] = {}
        for column, field_name in sorted(headers.items()):
            cell_id = f"{prefix}_tdrow_[C:{column}]-c[R:{row_number}]"
            cell = row_node.find(id=cell_id)
            if cell is None:
                record[field_name] = False if field_name == "ATP故障" else ""
            else:
                record[field_name] = _cell_value(
                    cell, is_checkbox=field_name == "ATP故障"
                )
        rows.append(record)
    return rows


def parse_fault_notice_page_info(response_text: str) -> FaultNoticePageInfo:
    decoded, soup = _parse_maximo_markup(response_text)
    if "沒有要顯示的列" in decoded:
        return FaultNoticePageInfo(0, 0, 0, None)

    table_prefixes: set[str] = set()
    for node in soup.find_all(id=HEADER_ID_RE):
        match = HEADER_ID_RE.match(str(node.get("id")))
        label = node.get_text(" ", strip=True).split("[", 1)[0].strip()
        if match is not None and label == "通報號":
            table_prefixes.add(match.group("prefix"))
    for node in soup.select(".tCount"):
        count_match = PAGE_COUNT_RE.fullmatch(node.get_text(" ", strip=True))
        id_match = COUNT_ID_RE.match(str(node.get("id", "")))
        if count_match is None or id_match is None:
            continue
        if id_match.group("prefix") not in table_prefixes:
            continue

        start = int(count_match.group("start"))
        end = int(count_match.group("end"))
        total = int(count_match.group("total"))
        if start < 1 or end < start or total < end:
            raise MMISClientError("故障通報分頁範圍無效")

        prefix = id_match.group("prefix")
        next_page_target: str | None = None
        for image in soup.find_all(
            "img",
            id=re.compile(rf"^{re.escape(prefix)}-ti\d+_img$"),
            src=re.compile(r"tablebtn_next_on\.gif$"),
        ):
            anchor = image.find_parent("a", id=True)
            if anchor is not None:
                next_page_target = str(anchor["id"])
                break
        return FaultNoticePageInfo(start, end, total, next_page_target)

    raise MMISClientError("查詢回應找不到故障通報總筆數")
