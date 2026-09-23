# 程式碼搜尋指南

狀態：範本佔位符。

## 搜尋入口

| 需求 | 從這裡開始 | 搜尋關鍵字 |
|---|---|---|
| CLI 子命令 | `src/mmis_connector/cli.py` | `QUERY_*_COMMAND`, `_commands` |
| 登入與網路邊界 | `src/mmis_connector/auth.py` | `MMISSession`, `MMISConfig`, `PageState` |
| Maximo event | `src/mmis_connector/events.py` | `MaximoEventClient`, `load_app`, `post` |
| 查詢功能 | `src/mmis_connector/query_*.py` | `Query`, `run` |
| 表格解析 | `src/mmis_connector/parser.py` | `parse_maximo_table`, `parse_*_page_info` |
| 測試 | `tests/test_*.py` | 對應功能模組或共用層名稱 |

## 已知符號

| 符號 | 意義 | 位置 |
|---|---|---|
| `MMISSession` | 登入、同源 HTTPS、timeout 與程序內 session | `src/mmis_connector/auth.py` |
| `MaximoEventClient` | 共用 Maximo event POST 與 app 切換 | `src/mmis_connector/events.py` |
| `DailyInspectionWorkOrderQuery` | 依車號與日期查詢 1A 工單 | `src/mmis_connector/query_daily_inspection_work_orders.py` |
| `DailyInspectionWorkOrderDetailReader` | 依工作單號進入 1A 工單並讀取故障通報管理 | `src/mmis_connector/read_daily_inspection_work_order.py` |
| `UnprocessedFaultNoticeQuery` | 查詢本段未處理通報 | `src/mmis_connector/query_unprocessed_fault_notices.py` |

## 給 Agent 的備註

- 優先做精確符號搜尋，再做大範圍文字搜尋。
- 發現對未來任務有幫助的搜尋結果時，記錄在這裡。
