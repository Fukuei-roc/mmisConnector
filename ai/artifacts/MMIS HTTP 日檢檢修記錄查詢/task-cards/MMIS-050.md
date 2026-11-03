# AI-Ready 任務卡

## Metadata

- 任務：MMIS-050 新增日檢檢修記錄填報完整性布林值
- 上層規格：`ai/artifacts/MMIS HTTP 日檢檢修記錄查詢/feature-spec.md` 2026-11-03 擴充
- 上層 Epic：MMIS HTTP 日檢檢修記錄查詢
- 上層 User Story：判斷檢修記錄填報完整性
- 分軌：後端
- 前置任務：無
- 狀態：完成
- 風險等級：中，沿用既有 MMIS 唯讀查詢與驗證
- Agent owner：Codex
- 人工核准者：專案使用者，2026-11-03 直接要求實作

## 目標與情境包

- 目標：讓 CLI 使用者直接得知所有檢修紀錄的回報結果是否已填報。
- 相關檔案：`src/mmis_connector/daily_inspection/reader.py`、`tools/mmis_development/query_daily_inspection_work_order_details.py`、`tests/test_daily_inspection_inspection_records.py`、指定錄製 DOM。
- 既有模式：reader 跨頁解析所有列，僅將備註非空列加入輸出；wrapper 依固定順序組裝 JSON。
- 假設：零筆紀錄的全稱條件為真。
- 未知事項：Live MMIS 憑證與網路是否可用。
- 允許變更：上述程式與測試、development tool README、本 Epic 規格及驗證文件、對應看板卡片。
- 不得觸碰：登入流程、MMIS 遠端資料、外部錄製檔、其他工單查詢。
- 情境預算：讀取專案地圖、reader 與 wrapper 相關段落、既有測試及錄製摘要與最終 DOM；跳過無關功能。

## 需求與驗收標準

- 新欄位 `maintenance_records_complete` 為 JSON 布林值，緊接 `開單日期`。
- 對所有分頁的每列「回報結果」去除空白後判斷；任一空值為 `false`，全部有值為 `true`。
- 判斷包含備註空白的列；現有 `檢修記錄.records` 篩選與其他欄位維持原契約。
- 分頁不完整或表格缺失時仍回報錯誤。

## 實作與驗證契約

- API：讀取單一工單號，成功 JSON 新增上述欄位；無資料庫或遷移。
- 安全：不記錄憑證、cookie、token 或完整錄製內容，不修改 MMIS。
- 驗證：執行對應 pytest、`git diff --check`、錄製 DOM 39 筆結果核對，條件允許時執行指定工單的 Live CLI。
- 螢幕截圖：不適用，沒有 UI 變更。
- 回滾：移除新欄位與 reader 的完成性計算。

## 完成證據

見 `verification/MMIS-050.md`。獨立審查提出的錄製 DOM 筆數斷言已補齊並重測。
