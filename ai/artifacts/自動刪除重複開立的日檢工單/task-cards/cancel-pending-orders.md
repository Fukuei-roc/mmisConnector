# AI-Ready 任務卡

## Metadata

- 任務：取消快照中待取消的重複日檢工單
- 上層規格：`../feature-spec.md`
- 上層 Epic：自動刪除重複開立的日檢工單
- 上層 User Story：自動完成已判定的重複工單取消
- 分軌：後端
- 前置任務（dependsOn）：`reconcile-duplicate-vehicles.md` 的候選判定程式
- 狀態：審查中
- 風險等級：高，涉及 MMIS 遠端寫入與本機 SQLite
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-09 明確要求新增此行為

## 目標

完成快照後，依序取消「待工單取消」的工單，確認成功後將其狀態更新為「已取消工單」。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_delete_duplicate_daily_inspection_work_orders.py`、`src/mmis_connector/daily_inspection/cancel.py`、`tests/test_unassigned_daily_inspection_work_orders.py`。
- 既有模式：單一 MMIS session；取消元件會檢查未派工狀態、送出取消事件、回讀確認。
- 假設：「待工單取消」由已核准的日期判定邏輯產生；資料庫列順序代表處理順序。
- 未知事項：Live MMIS 在目前環境中的實際取消回應。
- 允許變更的檔案：本任務的 development tool、測試、README、本 Epic 規格、任務卡與驗證紀錄。
- 不得觸碰：取消元件的遠端事件順序、其他 MMIS 業務流程、現有 SQLite 真實資料。
- 情境預算：讀取專案地圖、流程、候選判定與取消元件；跳過不相關的故障通報和 UI。

## 需求與契約

- API：CLI 無參數；取消函式接受資料庫路徑與既有取消元件的 `run(工作單)`。
- 資料模型：沿用六欄 SQLite schema，只有「執行結果」從「待工單取消」改為「已取消工單」。
- 驗證：遠端回應必須含 `success=True`、相同工作單及 `工作單狀態=工單取消`。
- 錯誤處理：失敗時停止整批；已確認列保留完成狀態，未確認列保留待取消狀態。
- 身分驗證：重用查詢階段建立的 MMIS session，憑證仍由環境載入。
- 遷移與回滾：無 schema 遷移；已取消的遠端工單無法用 SQLite 回滾。

## 驗收與驗證契約

- 單元測試：候選列依序取消、成功後改狀態、重跑時跳過已完成列、失敗時停止、錯誤回應不改狀態。
- 整合測試：執行目標 pytest 與完整 pytest。
- E2E：不在自動驗證中取消真實工單；需受控工單方可做 Live 驗證。
- 型別檢查／Lint／Build：`compileall`、`git diff --check`。
- 螢幕截圖：無 UI。
- 安全性檢查：取消前後驗證業務鍵與工單狀態；SQL 參數化；不記錄密鑰。

## 完成證據

- 見 `../verification/cancel-pending-orders.md`。
