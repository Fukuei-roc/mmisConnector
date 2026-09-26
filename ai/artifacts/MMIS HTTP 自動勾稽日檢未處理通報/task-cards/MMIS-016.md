# AI-Ready 任務卡

## Metadata

- 任務：修正自動勾稽的來源車號正規化
- 上層規格：`ai/artifacts/MMIS HTTP 自動勾稽日檢未處理通報/feature-spec.md`
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：尋找日檢工單與自動勾稽
- 分軌：後端
- 前置任務（dependsOn）：`MMIS-014`
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-26）

## 目標

將未處理通報的單車車號轉為日檢工單實際使用的數字查詢值，避免所有資料列被錯誤判為無對應工單。

## 情境包（Context Pack）

- 相關檔案：自動勾稽 orchestrator、其離線整合測試、功能規格、README 與治理 artifacts。
- 既有模式：來源原值完整保存於 SQLite；領域轉換在 orchestrator；通用 query 只驗證呼叫者提供的值；寫入 fail closed 且不 retry。
- 假設：900 型單車碼可由「移除非數字後為首位 9 的四位數」辨識，末位是車廂碼。
- 未知事項：無阻擋事項；使用者已確認 `EP9393 -> 939`。
- 允許變更的檔案：`src/mmis_connector/auto_link_unprocessed_fault_notices_to_daily_inspection_work_orders.py`、`tests/test_auto_link_unprocessed_fault_notices.py`、`README.md` 與本 Epic 規格／任務／驗證 artifacts、看板卡片。
- 不得觸碰：通用日檢 query 公開契約、linker、SQLite schema／既有 runtime DB、live MMIS 資料。

## 需求

- 移除來源車號所有非數字字元。
- 首位為 9 的四位數視為 900 型單車碼，移除最後一位。
- 其他數字保持不變。
- 無數字的來源列標記 `invalid_source_data`，不得查詢或勾稽。
- SQLite 保留原始來源車號，不覆寫為正規化值。

## 驗收標準

- `EP9393`、`EM9393`、`EP9503`、`ED9501`、`EM9422` 分別查詢 `939`、`939`、`950`、`950`、`942`。
- `EMU946`、`EMC722`、`ED883`、`EP884` 分別查詢 `946`、`722`、`883`、`884`。
- 已是純數字的 `717` 維持 `717`。
- 無數字輸入不呼叫 query/linker。
- 既有續跑、工單選擇與 fail-closed 測試不回歸。

## 實作備註

- 新增 orchestrator 專用的小型 pure function，不改 `normalize_vehicle()`。
- 先沿用 `normalize_vehicle()` 的空白輸入檢查，再執行數字擷取與 900 型規則。
- 不讀寫或遷移既有 SQLite schema。

## 驗證契約

- 單元測試：上述代表車號的參數化正規化測試、無數字錯誤。
- 整合測試：fake query 必須收到正規化值；真 SQLite 仍保存原值。
- E2E 測試：不執行 live mutation；修正後由人工受控驗收。
- 型別檢查：專案未配置。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tests`、`python -m pip check`。
- 螢幕截圖：不適用。
- 安全性檢查：錯誤輸出去敏、無新的檔案／網路／retry 行為。

## 完成證據

- 變更的檔案：自動勾稽 orchestrator、其離線測試、README、程式碼搜尋指南與本 Epic 治理 artifacts。
- 執行過的指令：實作前失敗測試、針對性 pytest、完整 pytest、compileall、pip check、diff check。
- 測試輸出：21 項針對性測試通過；完整回歸 119 passed、3 optional fixture skipped；語法、依賴與 diff 檢查通過。
- 螢幕截圖：不適用。
- 已知限制：900 型辨識依「首位 9 的四位數」業務規則；本次 live 資料沒有可勾稽工單，因此未由批次產生實際 mutation。
- 後續任務：無；新車型或其他車號編碼出現時另立規則擴充卡。
