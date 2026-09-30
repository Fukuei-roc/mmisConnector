import mmis_connector
from mmis_connector import (
    AutoLinkUnprocessedFaultNotices,
    DailyInspectionWorkOrderDetailReader,
    DailyInspectionWorkOrderFaultNoticeLinker,
    DailyInspectionWorkOrderQuery,
    FaultNoticeAnalysisReader,
    MMISClientError,
    MMISConfig,
    MMISSession,
    PageState,
    UnclosedFaultNoticeQuery,
    UnprocessedFaultNoticeQuery,
)
from mmis_connector.fault_notices.query import QUERY_NAME


def test_package_public_api_is_preserved() -> None:
    assert set(mmis_connector.__all__) == {
        "AutoLinkUnprocessedFaultNotices",
        "DailyInspectionWorkOrderDetailReader",
        "DailyInspectionWorkOrderFaultNoticeLinker",
        "DailyInspectionWorkOrderQuery",
        "FaultNoticeAnalysisReader",
        "MMISClientError",
        "MMISConfig",
        "MMISSession",
        "PageState",
        "UnclosedFaultNoticeQuery",
        "UnprocessedFaultNoticeQuery",
    }
    assert all(
        symbol is not None
        for symbol in (
            MMISClientError,
            MMISConfig,
            MMISSession,
            PageState,
        )
    )


def test_unprocessed_fault_notice_query_is_public() -> None:
    assert UnprocessedFaultNoticeQuery.__name__ == "UnprocessedFaultNoticeQuery"
    assert QUERY_NAME == "本段未處理通報(車輛配屬段)"


def test_unclosed_fault_notice_query_is_public() -> None:
    assert UnclosedFaultNoticeQuery.__name__ == "UnclosedFaultNoticeQuery"


def test_fault_notice_analysis_reader_is_public() -> None:
    assert FaultNoticeAnalysisReader.__name__ == "FaultNoticeAnalysisReader"


def test_daily_inspection_work_order_query_is_public() -> None:
    assert DailyInspectionWorkOrderQuery.__name__ == "DailyInspectionWorkOrderQuery"


def test_daily_inspection_work_order_detail_reader_is_public() -> None:
    assert (
        DailyInspectionWorkOrderDetailReader.__name__
        == "DailyInspectionWorkOrderDetailReader"
    )


def test_daily_inspection_work_order_fault_notice_linker_is_public() -> None:
    assert (
        DailyInspectionWorkOrderFaultNoticeLinker.__name__
        == "DailyInspectionWorkOrderFaultNoticeLinker"
    )


def test_auto_link_unprocessed_fault_notices_is_public() -> None:
    assert (
        AutoLinkUnprocessedFaultNotices.__name__
        == "AutoLinkUnprocessedFaultNotices"
    )
