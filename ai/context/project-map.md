# 專案地圖

狀態：已更新（2026-10-02）。

在專案導入（intake）時填寫這份文件。

## 產品

- 名稱：MMIS Connector
- 使用者：需要以命令列查詢或執行已授權 MMIS 操作的內部使用者
- 核心工作流程：讀取環境變數 → HTTP 登入 → 重用 Session → 切換目標 MMIS app → 送出 Maximo event → 驗證回應 → 輸出 JSON

## 技術棧

- 前端：無（CLI）
- 後端：Python 3.11、requests、Beautiful Soup
- 資料庫：無
- 身分驗證：MMIS 表單登入，憑證由 `.env` 載入，登入狀態只保留於程序內的 `requests.Session`
- 測試：pytest、錄製 DOM fixture
- 部署：Windows 本機 CLI

## 重要目錄

| 路徑 | 用途 | 備註 |
|---|---|---|
| `src/mmis_connector/` | HTTP client、共用 Maximo event、功能工作流程與 CLI | 不得依賴瀏覽器 |
| `tests/` | 單元與錄製證據解析測試 | 不存放敏感 HAR |
| `docs/development/` | MMIS 功能開發流程、已驗證元件與 reference 規則 | 不作 runtime dependency |
| `tools/mmis_development/` | 五個 MMIS 開發／診斷 executable wrappers | Production 不得 import |
| `ai/artifacts/` | 規格、任務卡、驗證證據 | 不記錄憑證或 token |

## 常用指令

| 指令 | 用途 | 備註 |
|---|---|---|
| `python -m tools.mmis_development.query_unprocessed_fault_notices` | Development tool：查詢本段未處理通報 | 需先設定 `.env` |
| `python -m tools.mmis_development.query_unclosed_fault_notices` | Development tool：查詢新竹機務段 A/B 級未結案故障通報 | 零參數、只輸出 stdout JSON |
| `python -m tools.mmis_development.query_fault_notice_analysis 1150828-12` | Development tool：依通報號讀取故障分析五欄 | 唯讀、只輸出 stdout JSON |
| `python -m tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice 1150210-36` | Development tool：依通報號讀取 ATP 故障分析三欄 | 唯讀；未勾選 ATP 時輸出 JSON 錯誤 |
| `python -m tools.mmis_development.query_work_orders_linked_to_fault_notice 1150910-14` | Development tool：依通報號讀取關聯段檢修工單 | 唯讀、跨頁並依工作單去重，只輸出 stdout JSON |
| `python -m tools.mmis_development.query_repair_work_orders_linked_to_fault_notice 1150930-09` | Development tool：依通報號讀取 CA 查修工單十欄 | 唯讀、跨頁並依工作單去重，只輸出 stdout JSON |
| `python -m tools.mmis_development.query_fault_notice_full_detail 1150210-36` | Development tool：整合基本資料、ATP 標記、段修與 CA 工單、故障分析 | 唯讀；六個基本欄位置於 JSON 第一層最前面，非 ATP 時分析為 null |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_by_vehicle_and_date 717 '>2026/09/23'` | Development tool：依車號與日期查詢日檢工單 | 需先設定 `.env` |
| `python -m tools.mmis_development.query_daily_inspection_work_order_by_number 115-1A-70048` | Development tool：依工作單號讀取故障通報 | 只輸出 stdout JSON |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C2-41266` | Development tool：依工作單讀取臨時檢修工單基本資料、已勾稽故障通報與維修程序概況 | 唯讀、只輸出 stdout JSON |
| `python -m tools.mmis_development.query_daily_inspection_work_order_by_number_and_link_fault_notice 115-1A-71002 1150923-36` | Development tool：勾稽指定故障通報 | 會變更 MMIS；需受控執行 |
| `python -m mmis_connector auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders` | 批次將未處理通報勾稽至最早的後續日檢工單 | 會變更 MMIS 資料；以 SQLite 續跑，`link_error` 不自動重送 |
| `python -m pytest` | 執行測試 | 不連線 MMIS 的測試為預設 |
