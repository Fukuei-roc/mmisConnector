# 驗證報告

## 摘要

- 任務：以英文顯示未送簽核日檢工單查詢執行結果
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest -q tests/test_query_daily_inspection_work_orders_not_submitted.py` | exit 0 | 9 個定向測試通過，檢查成功與失敗輸出。 |
| `python -m pytest -q` | exit 0 | 全套測試通過；條件性測試依本機資料狀態跳過。 |
| `python -m compileall -q tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py tools/mmis_development/_support.py` | exit 0 | 語法檢查通過。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval` | exit 0 | 顯示 `Status: SUCCESS`、`Records found: 8` 與資料庫相對路徑。 |
| 唯讀 SQLite `SELECT COUNT(*)` | 8 | 與 CLI 輸出的查詢筆數一致。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval unexpected` | exit 1 | 顯示 `Status: FAILED`、`Records found: unavailable`、路徑及 `MMISClientError`。 |
| `git diff --check` | exit 0 | 無空白錯誤；Git 提示部分檔案下次操作將轉為 CRLF。 |

## UI 證據

不適用。本任務無 UI。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 成功與失敗路徑均只輸出英文摘要，未輸出逐筆工單或原始例外訊息。 | 無 | 通過。 |
| `_support.py` 的共用 JSON 輸出旗標不再有呼叫者。 | 低 | 已移除，其他工具的預設行為未變。 |

## 殘留風險

- 查詢失敗時，資料庫路徑可能指向前次成功的快照。指令以 `Status: FAILED` 與非零結束碼區分本次結果。
- 本機資料庫包含 MMIS 工單與人員欄位。檔案已由 Git 忽略，未額外加密。
- 後續任務：無。
