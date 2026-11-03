# 驗證報告

## 摘要

- 任務：Excel 只匯出需通知檢車室的日檢工單。
- 結果：暫存 SQLite 與現有資料庫的實際 XLSX 驗證通過。未執行 Live MMIS 命令。
- 驗證者：Codex，2026-11-03。

## 變更與證據

- 匯出器先核對完整 SQLite 快照筆數，再篩選「備註欄」精確等於「通知檢車室」的資料，沿用五欄、排序、項次和樣式。
- 目標測試加入混合備註、較早日期未標註列及零筆符合案例，並以 openpyxl 讀取 XLSX。
- 現有資料庫唯讀檢查有 9 筆，其中 8 筆備註符合。匯出至暫存目錄後，Excel 有 8 筆資料、5 欄；逐列資料與 SQLite 篩選後依既有規則排序的結果相同。

## 指令

| 指令 | 結果 |
|---|---|
| `python -m pytest tests/test_query_daily_inspection_work_orders_not_submitted.py tests/test_unclosed_ab_xlsx.py tests/test_export_unclosed_ab_fault_notices_from_db.py -q -ra` | exit 0；兩個錄製 DOM 測試因本機無 fixture 跳過，其餘通過。 |
| `python -m compileall -q tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py tests/test_query_daily_inspection_work_orders_not_submitted.py` | exit 0，無輸出。 |
| `git diff --check` | exit 0，無空白錯誤。 |
| 現有 SQLite 唯讀讀取，再用 `export_snapshot_xlsx` 匯出到 `TemporaryDirectory` 並以 openpyxl 逐列比較 | exit 0；`PASS: SQLite total=9, notified=8, Excel rows=8, columns=5`。 |

## 審查與安全性

- 資料庫路徑沿用既有固定路徑；匯出使用共用模組的唯讀 SQLite 連線、完整 schema 檢查和獨占建立 XLSX 檔案。
- 比對值使用既有 `NOTIFICATION_NOTE` 常數；SQL 不插入使用者文字，文字儲存格仍由共用 XLSX 模組處理。
- 本次沒有 UI，截圖不適用。
- 獨立唯讀審查檢查架構、正確性、安全性與測試覆蓋，未發現問題，建議核准。未新增程式註解。

## 殘留風險與後續任務

- 未連線 Live MMIS，也未寫入 `.env` 指定的外部目錄；現場網路與目錄權限未驗證。
- 兩個錄製 DOM 測試因 fixture 缺少而跳過；這不影響本次 XLSX 篩選測試。
- 本次沒有必要的後續程式任務。
