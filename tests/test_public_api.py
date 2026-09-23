from mmis_connector import DailyInspectionWorkOrderQuery, UnprocessedFaultNoticeQuery
from mmis_connector.query_unprocessed_fault_notices import QUERY_NAME


def test_unprocessed_fault_notice_query_is_public() -> None:
    assert UnprocessedFaultNoticeQuery.__name__ == "UnprocessedFaultNoticeQuery"
    assert QUERY_NAME == "本段未處理通報(車輛配屬段)"


def test_daily_inspection_work_order_query_is_public() -> None:
    assert DailyInspectionWorkOrderQuery.__name__ == "DailyInspectionWorkOrderQuery"
