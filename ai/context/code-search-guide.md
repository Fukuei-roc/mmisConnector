# 程式碼搜尋指南

狀態：已更新（2026-09-29）。

## 搜尋入口

| 需求 | 從這裡開始 | 搜尋關鍵字 |
|---|---|---|
| Production CLI | `src/mmis_connector/cli.py` | `AUTO_LINK_*_COMMAND`, `_commands` |
| Development tools | `tools/mmis_development/` | `execute`, `main`, `USAGE` |
| 登入與網路邊界 | `src/mmis_connector/auth.py` | `MMISSession`, `MMISConfig`, `PageState` |
| Maximo event | `src/mmis_connector/events.py` | `MaximoEventClient`, `load_app`, `post`, `post_events` |
| 故障通報 domain | `src/mmis_connector/fault_notices/` | `UnprocessedFaultNoticeQuery`, `UnclosedFaultNoticeQuery`, `FaultNoticeAnalysisReader`, `run` |
| 日檢工單 domain | `src/mmis_connector/daily_inspection/` | `Query`, `Reader`, `Linker` |
| Auto-link application | `src/mmis_connector/auto_link/` | `orchestrator`, `store`, `AutoLink` |
| 表格解析 | `src/mmis_connector/parser.py` | `parse_maximo_table`, `parse_*_page_info` |
| 測試 | `tests/test_*.py` | 對應功能模組或共用層名稱 |
| 新 MMIS 功能／已驗證操作 | `docs/development/mmis-feature-workflow.md` | `Query`, `Reader`, `Linker`, `MaximoEventClient`, `parse_` |
| Auto-link 架構邊界 | `tests/test_architecture.py` | `CORE_MODULE`, `reachable`, `subprocess` |
| Production source 定位 | `docs/development/production-source-inventory.md` | `全檔案分類`, `Mixed-code`, `__init__.py` |

## 已知符號

| 符號 | 意義 | 位置 |
|---|---|---|
| `MMISSession` | 登入、同源 HTTPS、timeout 與程序內 session | `src/mmis_connector/auth.py` |
| `MaximoEventClient` | 共用 Maximo event POST 與 app 切換 | `src/mmis_connector/events.py` |
| `DailyInspectionWorkOrderQuery` | 依車號與日期查詢 1A 工單 | `src/mmis_connector/daily_inspection/query.py` |
| `DailyInspectionWorkOrderDetailReader` | 依工作單號進入 1A 工單並讀取故障通報管理 | `src/mmis_connector/daily_inspection/reader.py` |
| `DailyInspectionWorkOrderFaultNoticeLinker` | 對唯一 1A 工單勾稽指定故障通報、驗證結果並返回清單 | `src/mmis_connector/daily_inspection/linker.py` |
| `UnprocessedFaultNoticeQuery` | 查詢本段未處理通報 | `src/mmis_connector/fault_notices/query.py` |
| `UnclosedFaultNoticeQuery` | 以固定新竹機務段、A/B 級條件查詢未結案故障通報 | `src/mmis_connector/fault_notices/query.py` |
| `FaultNoticeAnalysisReader` | 依通報號唯一篩選並讀取故障分析五欄 | `src/mmis_connector/fault_notices/reader.py` |
| `FaultNoticeATPAnalysisReader` | 依通報號確認 ATP 勾選後讀取三欄 | `src/mmis_connector/fault_notices/atp_reader.py` |
| `normalize_auto_link_vehicle` | 將未處理通報單車碼轉為自動勾稽使用的數字查詢值；900 型四位碼去除末位車廂碼 | `src/mmis_connector/auto_link/orchestrator.py` |

## 給 Agent 的備註

- 優先做精確符號搜尋，再做大範圍文字搜尋。
- 發現對未來任務有幫助的搜尋結果時，記錄在這裡。
- 不要把 development tool 當成 production dependency；先追到 tool 實際建構的 Python component。
