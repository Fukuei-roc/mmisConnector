# AI-Ready 任務卡

## Metadata

- 任務：清查逾期工單
- 上層規格：`ai/artifacts/清查逾期工單/feature-spec.md`
- 上層 Epic：清查逾期工單
- 上層 User Story：執行命令建立當次逾期工單快照
- 分軌：後端
- 前置任務：無
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：使用者於本次任務明確授權實作與執行查詢

## 情境包

- 相關檔案：`src/mmis_connector/events.py`、`src/mmis_connector/parser.py`、`src/mmis_connector/daily_inspection/not_submitted.py`、`tools/mmis_development/README.md`。
- 錄製證據：`2026-11-05_query-overdue-work-orders` 的 HAR、DOM 與摘要。HAR 用於核對 app event；DOM 用於核對八欄和分頁。
- 既有模式：`MMISSession` 登入、`MaximoEventClient` 切換 app、表格解析器讀取分頁、SQLite 交易重建。
- 情境預算：只讀相關查詢、解析與資料庫範例，未檢閱其他工單明細模組。
- 允許變更：逾期查詢 component、開發工具、其測試、開發工具 README、此 Epic 產出物。
- 不得觸碰：錄製檔、正式 CLI、其他工單資料庫。

## 驗收標準與驗證契約

- 命令成功讀取全部結果頁，資料表包含八個指定欄位與最後的空白備註。
- 重跑清除舊資料與備註，查詢或寫入失敗保留舊資料。
- 執行 `python -m pytest tests/test_overdue_work_orders.py -q`。
- 執行 `python -m tools.mmis_development.audit_overdue_work_orders`，再以 SQLite 查詢欄位與筆數。
- 本任務沒有 UI 變更，無螢幕截圖要求。

## 完成證據

- 驗證報告：`ai/artifacts/清查逾期工單/verification/audit-overdue-work-orders.md`。
- 已知限制：目前快照反映 MMIS 該頁查詢結果；來源頁面說明其逾期統計每日中午更新一次。
