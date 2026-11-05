# 逾期工單 XLSX 版面與排序任務卡

## Metadata

- 上層 Epic：清查逾期工單
- 上層 User Story：以固定版面與三層排序檢視逾期工單 Excel
- 狀態：完成
- 風險等級：中，涉及匯出檔案格式與列順序，不修改 MMIS 或資料庫 schema
- 人工核准者：使用者於 2026-11-05 明確要求修改與驗證
- 前置任務：`audit-overdue-xlsx` 已完成

## 情境包

- 相關檔案：`tools/mmis_development/audit_overdue_work_orders.py`、`tools/mmis_development/_unclosed_ab_xlsx.py`、`tests/test_overdue_work_orders.py`、本 Epic 的功能規格與驗證文件。
- 既有模式：逾期工具在完成 SQLite 備註後讀取九欄，使用共用 `build_workbook` 建立樣式與 `save_workbook` 儲存檔案。
- 假設：資料庫欄位均為 TEXT；A 到 Z 以文字字典順序比較，三欄均升冪。
- 未知事項：固定 15.5 高度可能使多行備註無法完整顯示，仍依使用者指定值套用。
- 允許變更：逾期匯出工具、相應測試、README、本 Epic 規格、任務卡與驗證報告。
- 不得觸碰：共用 XLSX helper、其他匯出工具、MMIS 查詢元件、錄製檔、資料庫 schema。
- 情境預算：只讀逾期匯出函式、共用 workbook helper、相關測試與流程文件。

## 驗收標準

- 第 1 列高 16，所有資料列高 15.5，包括空白與多行備註。
- 九欄依欄名套用指定欄寬，順序及資料內容不變。
- Excel 依檢修級別、逾期天數、車組(輛) 三層文字升冪排序；SQLite 列順序不變。
- 無 `--export-xlsx` 時既有 CLI 行為不變；同名檔保護與錯誤處理維持。

## 驗證契約

- 執行相關 pytest，開啟真實 XLSX 比對欄寬、列高、三層排序與資料庫內容。
- 執行 compileall、`git diff --check`，並檢查本次產出的檔案。
- 無 UI，不需螢幕截圖。

## 完成證據

- 見 `ai/artifacts/清查逾期工單/verification/audit-overdue-xlsx-layout.md`。
