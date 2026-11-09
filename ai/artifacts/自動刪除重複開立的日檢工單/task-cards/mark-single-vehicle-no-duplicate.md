# AI-Ready 任務卡

## Metadata

- 任務：單筆車號標記無重複
- 上層規格：`../feature-spec.md`
- 上層 Epic：自動刪除重複開立的日檢工單
- 上層 User Story：從快照辨識每筆工單是否已完成重複檢查
- 分軌：後端
- 前置任務（dependsOn）：`reconcile-duplicate-vehicles.md`，既有功能已實作
- 狀態：完成
- 風險等級：高，涉及本機 SQLite 資料更新
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-09 明確要求修改程式邏輯及現有資料庫

## 目標

在「執行結果」明確標示已檢查且無重複的單筆車號。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_delete_duplicate_daily_inspection_work_orders.py`、`tests/test_unassigned_daily_inspection_work_orders.py`、本 Epic 規格與 `tools/mmis_development/README.md`。
- 既有模式：先替換完整快照，再按非空白車號分組；網路補查只處理重複組；核對快照版本後在短交易內寫結果。
- 假設：空白車號不視為可判定的單筆車號。
- 未知事項：未來 MMIS 清單中的車號是否會出現不同文字格式代表同一車組。
- 允許變更的檔案：本卡相關程式、測試、文件、驗證紀錄及使用者指定的本機 SQLite 快照。
- 不得觸碰：MMIS 遠端寫入、取消工單、資料庫 schema、其他功能。

## 需求與驗收標準

- 非空白車號僅出現一次時，該列「執行結果」為「無重複」。
- 重複組原有開單日期與取消候選判定不變；空白車號不標記。
- 單筆車號不查詢工單明細；現有快照 81 筆均可依此規則補寫。

## 驗證契約

- 單元測試：混合單筆與重複組、單筆與空白車號。
- 整合測試：直接讀取使用者指定 SQLite 的分組及「執行結果」。
- E2E 測試：無，更新現有快照不需要重新連線 MMIS。
- 型別檢查：本工具沒有獨立型別檢查設定。
- Lint／Build：`git diff --check` 與 `python -m compileall -q`。
- 螢幕截圖：無 UI。
- 安全性檢查：只使用參數化 SQL；快照核對與單一交易維持原流程。

## 完成證據

- 見 `../verification/mark-single-vehicle-no-duplicate.md`。
