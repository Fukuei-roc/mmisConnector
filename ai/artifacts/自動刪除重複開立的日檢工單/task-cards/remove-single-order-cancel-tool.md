# AI-Ready 任務卡

## Metadata

- 任務：移除單筆未派工日檢工單取消指令
- 上層規格：`../feature-spec.md`
- 上層 Epic：自動刪除重複開立的日檢工單
- 上層 User Story：保留自動取消重複工單的單一工具入口
- 分軌：後端
- 前置任務（dependsOn）：無
- 狀態：完成
- 風險等級：低；只移除 development CLI 入口，不修改 MMIS 取消元件
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-09 明確要求刪除指定指令

## 目標

確認自動取消工具不依賴單筆取消指令，然後移除單筆指令及其索引。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_delete_duplicate_daily_inspection_work_orders.py`、`tools/mmis_development/delete_unassigned_daily_inspection_work_order.py`、`tools/mmis_development/README.md`、`tests/test_architecture.py`。
- 既有模式：development 工具直接建構 `DailyInspectionWorkOrderCanceller`；production 不匯入 development 工具。
- 假設：使用者要求刪除的是 Python 指令入口，不是執行指令取消範例工單。
- 未知事項：無。
- 允許變更的檔案：單筆取消工具、工具 README、架構測試及本任務紀錄。
- 不得觸碰：自動取消流程、MMIS 遠端資料、真實 SQLite 快照。
- 情境預算：讀取專案地圖、架構地圖、搜尋指南、兩個工具、架構測試及 README；略過其他 MMIS 領域。

## 需求與驗收標準

- 自動取消工具不匯入或啟動被移除的單筆指令。
- 移除單筆指令，更新 README 工具數量及寫入風險說明。
- 架構測試列出剩餘的 16 個可執行工具並通過。
- 不執行會取消真實工單的命令。

## 驗證契約

- 單元與架構測試：執行日檢相關測試和完整 `pytest`。
- 靜態檢查：搜尋 `tools`、`src`、`tests` 中已移除的模組名稱，並執行 `git diff --check`。
- E2E：本次不執行 Live MMIS 寫入。
- 型別檢查、Build、螢幕截圖：未變更 Python 邏輯或 UI，不適用。
- 安全性檢查：確認自動流程仍直接使用既有取消元件，不改動遠端寫入邊界。

## 完成證據

- 見 `../verification/remove-single-order-cancel-tool.md`。
