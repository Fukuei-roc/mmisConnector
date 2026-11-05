# 逾期定期檢修工單狀態備註任務卡

## Metadata

- 上層 Epic：清查逾期工單
- 上層 User Story：建立逾期快照後標出未核簽或未結案的子工單
- 狀態：完成
- 風險等級：高，涉及 MMIS 網路查詢及本機資料庫寫入
- 人工核准者：使用者於 2026-11-05 明確要求實作與驗證
- 前置任務：`audit-overdue-work-orders` 已完成

## 情境包

- 相關檔案：`tools/mmis_development/audit_overdue_work_orders.py`、`src/mmis_connector/periodic_inspection/status.py`、`tests/test_overdue_work_orders.py`。
- 既有模式：單一 `MMISSession`，正式 query component，開發工具管理 SQLite 快照與輸出。
- 假設：`檢修級別` 精確等於 `2A` 或 `3A`；`records` 的順序是 MMIS 回傳順序。
- 未知事項：現場資料可能有空白狀態，依「非核簽中或工單結案」字面條件保留為 `工作單()`。
- 允許變更：上述開發工具、其測試、README、本 Epic 規格、任務卡和驗證報告，以及過時的專案地圖資料庫欄位。
- 不得觸碰：其他 MMIS 查詢元件、錄製檔、正式 CLI、其他資料庫。
- 情境預算：只讀逾期快照、定期檢修狀態查詢、相應測試與流程文件；未搜尋其他領域程式碼。

## 驗收標準

- 快照建立後，只按資料庫順序查詢 `2A`、`3A` 的主工單，並重用同一 MMIS session。
- 每筆排除狀態為 `核簽中`、`工單結案` 的子工單，依查詢順序組成 `工作單(工作單狀態)`，多筆以半形逗號連接。
- 寫入同一列的 `備註`，最後列印所有備註非空的完整資料列。
- 零筆、全排除、多筆及單筆查詢失敗有可檢查的結果。查詢失敗時資料庫保留已建立的空白備註快照，且命令以失敗結束。
- 不寫入遠端 MMIS；不呼叫子程序。

## 驗證契約

- 執行 `python -m pytest tests/test_overdue_work_orders.py -q`。
- 執行 `python -m compileall -q tools/mmis_development/audit_overdue_work_orders.py tests/test_overdue_work_orders.py`。
- 執行 `git diff --check`；若可連線，執行實際命令並查 SQLite 備註。
- 此任務無 UI，因此無螢幕截圖。

## 完成證據

- 見 `ai/artifacts/清查逾期工單/verification/audit-overdue-status.md`。
