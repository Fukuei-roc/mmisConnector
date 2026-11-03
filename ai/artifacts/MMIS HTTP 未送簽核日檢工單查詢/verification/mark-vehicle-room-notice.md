# 驗證報告

## 摘要

- 任務：已派工日檢工單明細符合條件時，更新 SQLite 備註欄。
- 結果：通過。2026-11-03 單一程序 Live 執行成功。
- 驗證者：Codex。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_query_daily_inspection_work_orders_not_submitted.py -q` | exit 0 | 涵蓋條件成立、檢修記錄未完成、兩種人員非空、其他狀態、明細失敗與 session 重用。兩項需本機錄製 DOM 的測試跳過。 |
| `python -m pytest -q` | exit 0 | 全部可執行測試通過；需外部錄製資料的測試依原有條件跳過。 |
| `python -m compileall -q tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py tests/test_query_daily_inspection_work_orders_not_submitted.py` | exit 0 | 語法檢查通過。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval` | exit 0 | `Status: SUCCESS`；`Records found: 9`；資料庫路徑符合契約。 |
| SQLite `SELECT "工作單狀態", "備註欄", COUNT(*) ... GROUP BY 1, 2` | exit 0 | 8 筆「執行中已派工」為「通知檢車室」；1 筆「工單退回」備註空白；總筆數 9。 |
| `git diff --check` | exit 0 | 沒有空白錯誤。 |

## UI 證據

CLI 與 SQLite 工作，無 UI 變更，不適用螢幕截圖。

## 審查發現

- 獨立審查確認新流程重用明細 Reader 與分組函式，與既有明細 JSON 的判斷一致。SQL 值已參數化；明細全部成功後才提交備註。
- 同時執行兩個程序時，現有整表重建可能與新明細查詢交錯，讓備註套到另一份快照。本任務依既有單一程序命令模式驗證；若需要並行執行，應另加互斥控制。

## 殘留風險

- MMIS 即時資料會變動。備註反映本次查詢時讀到的明細，不會隨遠端資料自動更新。
- 明細讀取中途失敗時，命令回報失敗，保留新快照且備註全部空白。重新執行可重建與重查。
- 本次未驗證兩個程序同時執行。

## 後續任務

- 只有在業務需要同時執行多個程序時，才新增跨程序互斥與相應測試。
