# 驗證報告

## 摘要

- 任務：成功輸出顯示檢車室通知筆數。
- 結果：通過。2026-11-03 Live 命令顯示 8 筆，SQLite 直接查詢也為 8 筆。
- 驗證者：Codex。

## 指令與結果

| 指令 | 結果 | 證據 |
|---|---|---|
| `python -m pytest tests/test_query_daily_inspection_work_orders_not_submitted.py -q` | exit 0 | 成功輸出涵蓋通知筆數 1 與 0；兩項需本機錄製 DOM 的測試跳過。 |
| `python -m pytest -q` | exit 0 | 全部可執行測試通過；外部錄製資料相關測試依原條件跳過。 |
| `python -m compileall -q tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py tests/test_query_daily_inspection_work_orders_not_submitted.py` | exit 0 | 無語法錯誤。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval` | exit 0 | `Status: SUCCESS`、`Records found: 9`、`Vehicle room notifications: 8`、資料庫路徑。 |
| SQLite `SELECT COUNT(*) ... WHERE "備註欄" = '通知檢車室'` | exit 0 | 資料庫實際筆數為 8。 |
| `git diff --check` | exit 0 | 沒有空白錯誤。 |

## 審查與限制

- 通知筆數由備註更新提交後的 SQLite 查詢取得，沒有新增 MMIS 寫入或個資輸出。
- CLI 無畫面變更，不適用螢幕截圖。
- 計數反映本次命令完成時的本機快照；既有的多程序同時重建快照風險未在本卡處理。
