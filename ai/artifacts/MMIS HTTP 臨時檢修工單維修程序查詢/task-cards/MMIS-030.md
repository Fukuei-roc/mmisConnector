# AI-Ready 任務卡

## Metadata

- 任務：擴充既有臨時檢修工單查詢的基本資料與 JSON 層級
- 上層規格：`ai/artifacts/MMIS HTTP 臨時檢修工單維修程序查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 上層 User Story：查詢維修程序
- 分軌：後端
- 前置任務（dependsOn）：MMIS-029 已完成並推送
- 狀態：審查中，待人工驗收
- 風險等級：中；沿用唯讀 MMIS HTTP 查詢，變更 stdout JSON 契約
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-05 明確指定八欄及 JSON 結構）

## 目標

原有指令依工作單讀取八個工單基本欄位至 JSON 最上層，將原紀事清單放入 `維修程序概況`。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/temporary_repair/reader.py`、`tests/test_temporary_repair_procedure.py`、`tools/mmis_development/README.md`、指定基本資料 HAR 與 DOM、MMIS-029 既有規格與驗證。
- 既有模式：重用同一次工單明細事件；用 label/for 找動態欄位；保留紀事清單九欄與補充文字處理。
- 風險區域：同名日期欄位重複，HAR 日期 `value` 和 `title` 可能皆為空；最上層與紀事列均有 `車組/車號`、`故障現象`，來源不可混淆。
- 未知事項：其他工單的空日期與多頁紀事尚無真實錄製。
- 允許變更的檔案：上述 reader、測試、工具 README、本 Epic 規格／任務／驗證、project map。
- 不得觸碰：`.env`、錄製檔、無關的 `Prompt.md`、其他工具。
- 情境預算備註：讀取工作流程、原 reader 與測試、基本資料錄製明細事件和 DOM、既有知識條目；略過 HAR 其餘靜態資源。

## 需求與驗收標準

- 最上層新增 `車組/車號`、`檢修級別`、`故障現象`、`原因說明`、`備註`、`檢修日期`、`完工日期`、`工作單狀態`，每欄均取工單明細。
- 原 `count`、`records` 移至最上層 `維修程序概況` 物件；多筆、一筆、空清單皆維持原紀事資料。
- 日期輸出 `YYYY/MM/DD`，同名重複欄位不一致時失敗；備註保留換行。
- 指定 HAR／DOM、C1 和 C2 即時查詢與原有測試通過。

## 實作備註

- 無新增 CLI 或登入流程；沿用 `MMISSession` 與現有 reader。
- JSON 契約調整會影響引用舊版最上層 `count`／`records` 的呼叫端，需改讀 `維修程序概況`。
- 無資料模型或遷移；回滾可還原本卡相關程式與文件變更。

## 驗證契約

- 單元測試：基本資料 HAR／DOM 八欄、重複日期衝突。
- 整合測試：原維修程序 HAR 兩筆、空清單與「其它」補充回歸。
- E2E 測試：C1 一筆與 C2 多筆即時查詢。
- 型別檢查／Lint／Build：`compileall`、`pip check`、`git diff --check`；專案無獨立型別檢查設定。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：仍只做查詢事件、不記錄憑證與 HAR、不輸出未要求的欄位。

## 完成證據

見 `verification/MMIS-030.md`。
