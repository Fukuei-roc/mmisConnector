# AI-Ready 任務卡

## Metadata

- 任務：在未送簽核日檢工單命令顯示檢車室通知筆數。
- 上層規格：`ai/artifacts/MMIS HTTP 未送簽核日檢工單查詢/feature-spec.md`。
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢。
- 上層 User Story：查詢並保留符合條件的日檢工單快照。
- 分軌：後端 CLI。
- 前置任務：`mark-vehicle-room-notice.md`，已完成。
- 狀態：完成。
- 風險等級：低。只增加成功輸出，不改變 MMIS 與 SQLite 寫入條件。
- Agent owner：Codex。
- 人工核准者：使用者於本次對話直接要求新增英文顯示。

## 目標與範圍

成功時顯示 `Vehicle room notifications: <count>`，其中筆數取自本次 SQLite 快照的「備註欄」等於「通知檢車室」的資料。失敗輸出、查詢與備註判斷不在本卡變更範圍。

## 情境包

- 相關檔案：`tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py`、`tests/test_query_daily_inspection_work_orders_not_submitted.py`。
- 既有模式：`mark_orders_requiring_personnel` 完成備註更新後返回整數；`execute` 組裝結果，`main` 輸出英文狀態。
- 假設：使用既有完整備註值「通知檢車室」，使用者所述「通知檢車」指同一標註。
- 未知事項：無。
- 允許變更：清單命令、對應測試、本規格、README、任務卡與驗證紀錄。
- 不得觸碰：明細 Reader、MMIS 認證、其他命令、Excel 欄位。
- 驗證指令：對應 pytest、完整 pytest、語法檢查、Live 命令、SQLite 計數、`git diff --check`。
- 情境預算：讀取專案地圖、相關命令與測試及完成定義；略過無關模組。

## 驗收標準

- 成功輸出新增一行英文通知筆數，位置在 `Records found` 與 `Database path` 之間。
- 筆數為實際 SQLite 備註欄等於「通知檢車室」的資料量；零筆顯示 `0`。
- 失敗輸出與 Excel 欄位維持原契約。

## 完成證據

- 見 `ai/artifacts/MMIS HTTP 未送簽核日檢工單查詢/verification/show-vehicle-room-notification-count.md`。
