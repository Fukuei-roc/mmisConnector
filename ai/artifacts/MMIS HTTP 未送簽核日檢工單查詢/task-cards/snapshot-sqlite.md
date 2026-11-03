# AI-Ready 任務卡

## Metadata

- 任務：將未送簽核日檢工單查詢結果改存 SQLite 快照
- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢
- 上層 User Story：內部使用者保留最新一次完整查詢結果供後續檢視
- 分軌：後端
- 前置任務：既有唯讀查詢已完成
- 狀態：完成
- 風險等級：高，涉及本機資料庫檔案與 MMIS 身分驗證、網路邊界
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-03 明確要求修改並實作驗證

## 目標

執行原指令後，在 `data/` 取得最新一次完整查詢的 SQLite 資料庫，成功時 stdout 為空。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py`、`src/mmis_connector/daily_inspection/not_submitted.py`、`tests/test_query_daily_inspection_work_orders_not_submitted.py`。
- 既有模式：查詢元件負責 MMIS 分頁與欄位驗證；development tool 負責輸出；其他本機快照使用 SQLite 交易。
- 假設：每筆 14 欄為所需「所有資料」；資料庫採 SQLite，檔名與指令一致。
- 未知事項：Live MMIS 在執行時可能沒有符合條件的工單。
- 允許變更的檔案：本工具、對應測試、`.gitignore`、工具 README、本 Epic 規格、任務卡與驗證報告。
- 不得觸碰：MMIS 寫入流程、查詢篩選條件、憑證檔、其他資料庫。
- 情境預算：閱讀本查詢、共用工具、既有 SQLite 快照與專案流程；跳過無關的故障分析實作。

## 需求

- 無參數，維持既有 MMIS 查詢與驗證。
- 完整查詢成功後，於單一交易中重建 14 欄資料表並寫入本次全部資料。
- 零筆結果清空前次資料；查詢或寫入失敗保留前次成功結果。
- 成功時 stdout 為空；錯誤維持共用工具格式。
- 本機資料庫須由 Git 忽略。

## 驗收標準

- 查詢結果的 14 欄、筆數與布林值在 SQLite 中正確。
- 重跑後無舊列；零筆結果為空表。
- 寫入失敗回滾；成功時 stdout 為空。

## 實作備註

- 使用 Python 標準函式庫 `sqlite3`，不新增依賴。
- 使用工作單主鍵避免重複資料，`逾期標註` 儲存為 0/1。
- 每次交易先刪除舊表再建立新表，因此舊 schema 與舊資料一起替換；交易失敗會回滾。

## 驗證契約

- 單元測試：快照替換、空結果、完整欄位、交易回滾、CLI 成功靜默及錯誤輸出。
- 整合測試：既有分頁測試與實際指令查詢。
- E2E 測試：實際指令成功時直接查詢 SQLite 筆數與欄位。
- 型別檢查：專案未設獨立指令。
- Lint：專案未設獨立指令。
- Build：`python -m compileall -q`。
- 螢幕截圖：無 UI。
- 安全性檢查：資料庫 Git 忽略、SQL 識別名稱固定、值以參數綁定、憑證不入庫。

## 完成證據

- 見 `../verification/snapshot-sqlite.md`。
