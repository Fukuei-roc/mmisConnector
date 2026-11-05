# 逾期工單 XLSX 匯出任務卡

## Metadata

- 上層 Epic：清查逾期工單
- 上層 User Story：一鍵重建逾期快照並輸出 Excel
- 狀態：完成
- 風險等級：高，涉及 MMIS 網路查詢、本機資料庫與檔案寫入
- 人工核准者：使用者於 2026-11-05 明確要求實作與驗證
- 前置任務：`audit-overdue-status` 已完成

## 情境包

- 相關檔案：`tools/mmis_development/audit_overdue_work_orders.py`、`tools/mmis_development/_unclosed_ab_xlsx.py`、`tests/test_overdue_work_orders.py`、`tools/mmis_development/README.md`。
- 既有模式：CLI 先重建 SQLite；匯出工具以 `read_snapshot` 驗證 schema 與筆數，再用 `build_workbook`、`save_workbook` 產生不覆蓋的 XLSX。
- 假設：`--export-xlsx` 每次都先執行既有 MMIS 查詢與備註更新；無旗標時維持原有行為。
- 未知事項：使用者未指定同名檔案處理方式，沿用現有工具的數字後綴。
- 允許變更：逾期 CLI、相應測試、README、本 Epic 規格、架構與驗證文件。
- 不得觸碰：其他查詢元件、共用 XLSX 實作、錄製檔、正式 CLI、其他資料庫。
- 情境預算：只讀逾期 CLI、共用 XLSX、相鄰匯出 CLI 與測試；跳過其他領域模組。

## 驗收標準

- `python -m tools.mmis_development.audit_overdue_work_orders --export-xlsx` 完成快照與備註後，輸出全部資料列和九欄，包含備註空白列。
- 檔案存於 `UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR`，名稱採台北系統日期 `MMDD`，同名檔案不被覆蓋。
- 字型為微軟正黑體 12 點；標題列置中，資料列靠左，與現有工具一致。
- 無旗標時不產生檔案；無效旗標、資料夾設定錯誤或匯出失敗時，以非零結束碼回報。匯出失敗時保留已完成的 SQLite 快照。
- 不寫入遠端 MMIS；不把憑證或個人資料寫入版本控制。

## 驗證契約

- 執行逾期 CLI 和相關 XLSX 測試，檢查實際 XLSX 儲存格、格式與筆數。
- 執行 `python -m compileall -q`、`git diff --check`。
- 若設定目錄可寫，執行實際 `--export-xlsx` 並回讀檔案驗證。
- 無 UI，不需螢幕截圖。

## 完成證據

- 見 `ai/artifacts/清查逾期工單/verification/audit-overdue-xlsx.md`。
