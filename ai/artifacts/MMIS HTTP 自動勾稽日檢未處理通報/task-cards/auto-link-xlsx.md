# AI-Ready 任務卡

## Metadata

- 任務：自動勾稽結果匯出 Excel。
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報。
- 狀態：已核准，使用者於 2026-11-09 直接要求實作。
- 風險等級：高，涉及本機資料庫讀取及指定資料夾寫檔。
- 前置任務：MMIS-063 已完成。

## 情境包

- 目標：正式 CLI 支援 `--export-xlsx`，成功執行後輸出 11 欄結果表。
- 相關檔案：`src/mmis_connector/cli.py`、`auto_link/store.py`、`tools/mmis_development/_unclosed_ab_xlsx.py`、CLI 與架構測試。
- 既有模式：CLI 參數先驗證；SQLite 結果表欄序由 `RESULT_COLUMNS` 定義；匯出路徑取 `.env`；Excel 使用微軟正黑體 12pt，表頭置中、資料靠左。
- 假設：「所有欄位」指提供使用者檢視的 `fault_notices` 11 欄，不含續跑用的內部表。
- 未知事項：無。
- 允許變更：匯出模組、CLI、相關測試、功能規格及驗證紀錄。
- 不得觸碰：MMIS 查詢與遠端寫入流程、現有 SQLite 資料。
- 驗證：離線測試、完整 pytest、compileall、pip check、diff check，以及實際 SQLite 與 XLSX 逐列比對。
- 情境預算：只讀 CLI、結果表 schema、現有匯出器、相關測試與流程文件；略過無關 MMIS 頁面解析。

## 契約

- 無參數命令維持既有行為。`--export-xlsx` 僅在勾稽成功後匯出。
- 輸出路徑由 `UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR` 指定，資料夾必須已存在。
- Excel 保留原欄序及文字內容，字串不得成為公式；失敗時回報錯誤，不改寫 SQLite。
- 開發階段僅以既有資料庫驗證匯出，不執行 MMIS 查詢。
