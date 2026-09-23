from pathlib import Path

import pytest

from mmis_connector.auth import MMISClientError
from mmis_connector.parser import (
    FaultNoticePageInfo,
    parse_fault_notice_page_info,
    parse_fault_notice_table,
)


RECORDED_DOM = Path(
    r"C:\Docker\maximoFlowRecorder\recordings"
    r"\2026-09-23_query-multi-page-unprocessed-reports\dom"
    r"\2026-09-23T024330-435.html"
)


def test_parse_recorded_dom_extracts_all_rows_and_fields() -> None:
    rows = parse_fault_notice_table(RECORDED_DOM.read_text(encoding="utf-8"))
    assert len(rows) == 2
    assert len(rows[0]) == 17
    assert set(rows[0]) == {
        "車次",
        "車組/車號",
        "發生日期",
        "發生時間",
        "事故等級",
        "故障地點",
        "ATP故障",
        "故障現象",
        "立案人員",
        "通報人員",
        "通報單位",
        "通報股室",
        "狀態",
        "通報號",
        "配屬段別",
        "配屬段別名稱",
        "顏色查詢",
    }
    assert isinstance(rows[0]["ATP故障"], bool)


def test_empty_result_is_not_a_parse_failure() -> None:
    assert parse_fault_notice_table("<message>沒有要顯示的列。</message>") == []


def test_parse_page_info_finds_total_and_enabled_next_page() -> None:
    response = """
    <component><![CDATA[
      <div id="table123_ttrow_[C:1]_ttitle-lb">通報號</div>
      <label id="table123-lb3" class="tCount">&nbsp;1 - 20/22</label>
      <a id="table123-ti7"><img id="table123-ti7_img"
        src="tablebtn_next_on.gif" /></a>
    ]]></component>
    """

    assert parse_fault_notice_page_info(response) == FaultNoticePageInfo(
        start=1,
        end=20,
        total=22,
        next_page_target="table123-ti7",
    )


def test_parse_page_info_last_page_has_no_next_target() -> None:
    response = """
    <div id="table123_ttrow_[C:1]_ttitle-lb">通報號</div>
    <label id="table123-lb3" class="tCount">21 - 22/22</label>
    <a id="table123-ti7"><img id="table123-ti7_img"
      src="tablebtn_next_off.gif" /></a>
    """

    assert parse_fault_notice_page_info(response) == FaultNoticePageInfo(
        start=21,
        end=22,
        total=22,
        next_page_target=None,
    )


def test_parse_page_info_requires_total_count() -> None:
    with pytest.raises(MMISClientError, match="總筆數"):
        parse_fault_notice_page_info("<div>有資料但沒有計數元件</div>")


def test_parse_page_info_uses_count_from_fault_notice_table() -> None:
    response = """
    <div id="other_ttrow_[C:1]_ttitle-lb">其他欄位</div>
    <label id="other-lb3" class="tCount">1 - 1/999</label>
    <div id="fault_ttrow_[C:1]_ttitle-lb">通報號</div>
    <label id="fault-lb3" class="tCount">1 - 20/22</label>
    <a id="fault-ti7"><img id="fault-ti7_img"
      src="tablebtn_next_on.gif" /></a>
    """

    assert parse_fault_notice_page_info(response).total == 22
