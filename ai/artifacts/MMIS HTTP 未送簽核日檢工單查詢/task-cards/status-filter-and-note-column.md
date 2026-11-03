# AI-Ready 任務卡

## Metadata

- 任務：擴大日檢工單狀態篩選並在 SQLite 最右側新增空白備註欄。
- 上層規格：`ai/artifacts/MMIS HTTP 未送簽核日檢工單查詢/feature-spec.md`。
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢。
- 上層 User Story：查詢並保留符合條件的日檢工單快照。
- 分軌：後端。
- 前置任務：無。
- 狀態：完成。
- 風險等級：高。現有查詢跨 MMIS 網路，且本次調整 SQLite 結構。
- Agent owner：Codex。
- 人工核准者：使用者於本次對話直接指定篩選值與資料庫欄位。

## 目標

以指定的十種工作單狀態查詢，並在 SQLite 快照最後新增空白的備註欄。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/daily_inspection/not_submitted.py`、`tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py`、對應測試。
- 既有模式：MMIS 篩選列用逗號分隔多值；查詢結果逐列驗證；SQLite 在單一交易中重建快照。錄製檔證實進入 1A 後必須清空配屬段預設值，再直接過濾，不切換「所有記錄」。
- 假設：備註欄只屬於 SQLite，不新增至 MMIS JSON 或五欄 Excel。
- 未知事項：無。錄製檔確認漏掉的配屬段清空事件造成 3 筆與 9 筆差異。
- 允許變更的檔案：上述程式與測試、本功能規格、任務卡及驗證紀錄。
- 不得觸碰：MMIS 認證、其他功能模組、Excel 欄位契約。
- 情境預算：閱讀專案地圖、相關查詢、SQLite wrapper、測試及 MMIS 查詢指南；略過無關功能。

## 需求與驗收標準

- 篩選值與使用者指定的十種狀態及順序完全相同。
- 進入 1A 後直接過濾，不執行「所有記錄」選單操作。
- 清空 1A 清單預設的配屬段篩選值。
- 逐列允許十種狀態，拒絕清單以外狀態。
- SQLite 第 15 欄為備註欄且值為空字串；舊資料保留。
- JSON、CLI 與五欄 Excel 的其他行為維持原樣。

## 實作與驗證契約

- 以單一狀態 tuple 建立篩選字串及逐列驗證清單。
- SQLite 重建時加入備註欄，現有本機資料庫用 `ALTER TABLE` 原地加欄。
- 執行對應 pytest、語法檢查、`git diff --check` 與資料庫直接查詢。
- 線上執行指定指令，核對預設清單的結果筆數與資料庫內容。
- 無 UI，無螢幕截圖；不變更認證、權限、密鑰或遠端 MMIS 資料。

## 完成證據

- 見 `ai/artifacts/MMIS HTTP 未送簽核日檢工單查詢/verification/status-filter-and-note-column.md`。
