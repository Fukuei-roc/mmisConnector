# AI-Ready 任務卡

## Metadata

- 任務：Excel 只匯出需通知檢車室的日檢工單
- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢
- 上層 User Story：將需通知檢車室的工單交付檢視
- 分軌：後端
- 前置任務：SQLite 快照、備註填寫及 Excel 匯出已完成
- 狀態：使用者於 2026-11-03 明確要求實作
- 風險等級：高，涉及既有 SQLite 讀取與本機 Excel 寫入
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-03 明確要求實作

## 目標

`--export-xlsx` 只輸出本次 SQLite 快照中「備註欄」精確等於「通知檢車室」的資料，再沿用原本排序、項次與五欄格式。

## 情境包（Context Pack）

- 相關檔案：目標工具、`_unclosed_ab_xlsx.py`、對應測試、本 Epic 規格。
- 既有模式：查詢和備註填寫先提交完整 SQLite 快照；匯出器讀取完整 schema 並核對快照總筆數，投影五欄後排序和編項次。
- 資料形狀：SQLite 每列是依 `DATABASE_FIELDS` 排列的 tuple，最右欄是「備註欄」。
- 風險區域：不要把篩後筆數拿來核對完整快照；零筆符合時仍須產生只有標題列的 Excel。
- 驗證指令：目標 pytest、`compileall`、`git diff --check`，並用 openpyxl 讀取產出的實際檔案。
- 情境預算：已讀專案地圖、工作流程、DoR/DoD、目標工具、共用 XLSX 模組、目標測試與既有規格；跳過無關 MMIS 查詢。
- 允許變更：目標工具、對應測試、本 Epic 規格及驗證報告。
- 非目標：不改 MMIS 查詢條件、SQLite schema、通知判斷、CLI 狀態欄位或 Excel 樣式。

## 資料與錯誤契約

- API 契約：`export_snapshot_xlsx(database_path, expected_records, ...)` 簽名不變；`expected_records` 仍指完整快照筆數。
- 資料模型與驗證：schema 不變，先核對完整快照筆數，再依備註篩選。
- 錯誤處理：沿用既有 SQLite、XLSX 錯誤與 CLI 失敗行為。
- 身分驗證與權限：沿用既有 MMIS session；匯出只讀 SQLite，使用既有輸出目錄。
- 遷移與回滾：無遷移；如需回滾，還原匯出篩選和測試即可。

## 驗收標準

- 混合備註快照只輸出精確符合的資料，並在篩選後依原規則排序、由 1 起編項次。
- XLSX 檔名、五欄、欄寬、列高、字型和對齊維持既有格式。
- `records_exported` 是篩後筆數；完整快照筆數核對仍有效。
- 零筆符合時 Excel 只有標題列。
- 既有無旗標行為與通知筆數維持原樣。

## 驗證契約

- 以 pytest 寫入暫存 SQLite，匯出並用 openpyxl 核對實際 XLSX。
- 執行相關 pytest、`compileall`、`git diff --check`。
- 不連線 Live MMIS，避免驗證時重建使用者的正式快照與寫入外部目錄。
- 無 UI，截圖不適用。
