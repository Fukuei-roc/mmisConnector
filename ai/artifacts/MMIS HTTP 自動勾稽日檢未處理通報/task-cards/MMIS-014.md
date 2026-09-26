# AI-Ready 任務卡

## Metadata

- 任務：實作自動勾稽批次領域編排器
- 上層規格：`ai/artifacts/MMIS HTTP 自動勾稽日檢未處理通報/feature-spec.md`
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：尋找日檢工單與自動勾稽
- 分軌：後端
- 前置任務（dependsOn）：`MMIS-013`
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-24）

## 目標

以單一 MMIS session 編排來源查詢、日檢工單選擇與故障通報勾稽，並將每筆結果安全寫入 SQLite。

## 情境包（Context Pack）

- 相關檔案：新 orchestrator、三個既有 query/linker 模組、新 store、新對應測試。
- 既有模式：HTTP-only、單一 session、`>YYYY/MM/DD`、動態表格、linker 寫入不 retry 且需領域驗證。
- 假設：來源 `通報號` 是 linker 的故障通報號。
- 未知事項：無阻擋事項；live 權限錯誤 DOM 未錄製，統一落為不可重試 `link_error`。
- 允許變更的檔案：新 orchestrator 與測試；若純測試注入需要，可對 store 做不改契約的小幅修正。
- 不得觸碰：既有 query/linker 公開契約、CLI、瀏覽器流程、transport retry。

## 需求

- 新 run 才擷取未處理通報；續跑不得重新擷取。
- 驗證來源三欄並送出車組／車號與 `>發生日期`。
- 工單依最早檢修日期決策，同日不同工單則拒絕勾稽。
- 單筆查詢錯誤記錄後繼續；零筆為正常終止狀態。
- 勾稽前先 commit `linking`；任何 linker 錯誤記錄 `link_error`，永不自動重跑。
- 所有列完成後更新 run 並輸出摘要資料。

## 驗收標準

- fake 依賴證明三個領域物件收到同一 client。
- 查詢參數精確為來源車號及 `>YYYY/MM/DD`。
- 工單零筆、一筆、多日多筆、同日歧義與重複列皆按規格處理。
- 一列錯誤不阻止後續列。
- linked／link_error 在續跑時均不再次呼叫 linker。
- `linking` crash window 不會自動重送。

## 實作備註

- 以依賴注入的工廠或 protocol 進行離線測試，避免不必要抽象。
- 捕捉單筆例外時僅保存安全、短小的領域錯誤摘要。
- 不以 subprocess 呼叫既有 CLI。

## 驗證契約

- 單元測試：來源驗證、日期、選單規則、狀態機、逐列容錯、摘要。
- 整合測試：真 SQLite + fake MMIS query/linker，模擬中斷與續跑。
- E2E 測試：未另行核准前禁止 live mutation。
- 型別檢查：專案未配置。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tests`。
- 螢幕截圖：不適用。
- 安全性檢查：mutation 不 retry、結果不明不重送、log/DB 去敏。

## 完成證據

- 變更的檔案：新 orchestrator、SQLite store 的執行鎖調整、新整合測試與本 Epic artifacts。
- 執行過的指令：targeted pytest、既有三能力回歸、compileall、diff check。
- 測試輸出：19 項新功能測試通過；合併回歸 62 passed、1 optional fixture skipped。
- 螢幕截圖：不適用。
- 已知限制：無跨 SQLite 與 MMIS 的分散式 transaction；以 `linking` fail-closed。link_error 需人工處理，不能自動開始新批次。
- 後續任務：`MMIS-015`。
