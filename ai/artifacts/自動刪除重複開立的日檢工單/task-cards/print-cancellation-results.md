# AI-Ready 任務卡

## Metadata

- 任務：在自動取消重複日檢工單後輸出中文結果
- 上層規格：`../feature-spec.md`
- 上層 Epic：自動刪除重複開立的日檢工單
- 上層 User Story：從終端直接確認沒有重複，或查看已取消的車組與工作單
- 分軌：後端 CLI
- 前置任務（dependsOn）：取消候選與單筆取消功能已實作
- 狀態：審查中
- 風險等級：低，僅變更輸出；既有指令仍會寫入 MMIS
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-09 明確要求

## 目標與範圍

- 無重複車組時印出「未發現重複的未派工日檢工單」。
- 有已取消工單時，每筆印出「已刪除的車組/車號：<車組/車號>，工作單：<工作單>」。
- 不改變候選判定、取消、資料庫 schema 或錯誤處理。

## 情境包

- 相關檔案：`tools/mmis_development/auto_delete_duplicate_daily_inspection_work_orders.py`、`tests/test_unassigned_daily_inspection_work_orders.py`、`tools/mmis_development/README.md`。
- 既有模式：`main()` 先收集 MMIS 查詢結果，再取得重複判定及本次確認取消的工作單。
- 假設：原始查詢結果中的工作單唯一，SQLite 主鍵也要求唯一。
- 未知事項：無。
- 允許變更：上述程式、測試、README、本 Epic 規格和驗證紀錄。
- 不得觸碰：MMIS 取消元件及其他工具。
- 情境預算：讀取專案地圖、就緒與完成定義、目標工具及測試；跳過其他 MMIS 功能。

## 契約與驗收

- 輸入與身分驗證：維持原 CLI 無參數及 MMIS session。
- 輸出：只有 `duplicate_groups == 0` 才印無重複訊息；只列出本次確認取消的工作單及其車組。
- 資料模型與遷移：無變更。
- 錯誤處理：沿用既有非零結束碼；不把未確認取消的工單印成已刪除。
- 驗證：以暫存 SQLite 及模擬 MMIS 查詢執行 `main()`，檢查兩種 stdout 與已取消狀態；執行完整 pytest、compileall 和 diff 檢查。

## 完成證據

- 見 `../verification/print-cancellation-results.md`。
