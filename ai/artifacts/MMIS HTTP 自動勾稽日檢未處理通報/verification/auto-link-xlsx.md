# 驗證報告

## 結果

- 新增正式 CLI 選項 `--export-xlsx`。既有無參數行為維持；正式執行時先呼叫既有勾稽流程，成功後才匯出。
- 開發驗證只直接呼叫唯讀匯出器，使用現有 `data/auto_link_unprocessed_fault_notices.sqlite3`，未啟動 MMIS Session 或重新查詢。
- 已在 `.env` 指定資料夾產生 `未處理故障通報日檢勾稽_程式產生1109.xlsx`。

## 證據

| 指令或檢查 | 結果 |
|---|---|
| `python -m pytest tests/test_cli.py tests/test_auto_link_xlsx.py -q` | 通過。 |
| `python -m pytest -q` | 通過，exit 0；既有條件性測試略過。 |
| `python -m compileall -q src tests` | 通過。 |
| `python -m pip check` | `No broken requirements found.` |
| `git diff --check` | 通過。 |
| 直接呼叫 `mmis_connector.auto_link.xlsx.export_xlsx()` | 使用現有 SQLite，產生 9 筆、11 欄 Excel。 |
| 使用 `openpyxl.load_workbook` 與 SQLite `SELECT * FROM fault_notices ORDER BY rowid` 逐列比對 | 表頭、9 筆資料及欄序全部相符；輸出檔 6337 bytes。 |

## 審查

- 架構：正式 CLI 只負責選項與編排；匯出器只讀結果表，不 import 開發工具，未改 MMIS 查詢或資料庫 schema。
- 安全：SQLite 使用唯讀 URI；輸出目錄須為已存在的絕對路徑；檔案以排他建立避免覆蓋；字串儲存格明確設為文字，防止公式執行；錯誤輸出不含資料列及憑證。
- 測試：涵蓋 CLI 先完成流程後匯出、11 欄內容、格式、公式樣字串及不改動測試資料庫。
- 審查結論：核准。無已知阻擋問題。

## 限制

- 依使用者要求，未執行會查詢或寫入 MMIS 的正式命令。正式命令與真實 MMIS 的串接只以隔離測試驗證。
- Excel 含故障通報資料，存放位置及存取權限由 `.env` 指定資料夾管理。
- 本任務無 UI 畫面變更，無螢幕截圖。
