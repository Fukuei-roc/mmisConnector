# AI-Ready 任務卡

## Metadata

- 任務：優化臨時檢修工單查詢順序
- 上層規格：`ai/artifacts/MMIS HTTP 臨時檢修工單維修程序查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 上層 User Story：查詢維修程序
- 分軌：後端
- 前置任務（dependsOn）：MMIS-031 已實作並推送
- 狀態：審查中，待人工驗收
- 風險等級：中；沿用唯讀 MMIS 查詢，但調整查詢範圍與事件順序
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-05 明確要求預設清單先查、零筆時回退）

## 目標

減少預設清單可查到的工單查詢延遲，同時維持「工單結案」與「工單取消」工單的可查性。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/temporary_repair/reader.py`、`src/mmis_connector/events.py`、`tests/test_temporary_repair_procedure.py`、指定速度優化錄製 HAR、原本兩份臨時檢修錄製、工具 README 與本 Epic 文件。
- 既有模式：單一 `MMISSession`、`MaximoEventClient`、動態表頭定位、setvalue→filterrows、完全相符與唯一性驗證、只在有效零筆結果時回退。
- 風險區域：預設查詢與所有記錄的表格、欄位與 xhr 序號；零筆結果不能與錯誤或尚未載入混淆；「所有記錄」切換會重設過濾條件。
- 假設：載入 app 的頁面回應含可辨識的「工作單」清單表頭。
- 未知事項：其他保存查詢是否有不同預設範圍；透過實際查詢結果驗證。
- 允許變更的檔案：上述事件 client、reader、測試、工具 README、project map、本 Epic 規格／任務／驗證。
- 不得觸碰：`.env`、錄製檔、已忽略的 `Prompt.md`、其他功能程式。
- 情境預算備註：只分析 HAR 中的 app 載入、兩次過濾與切換所有記錄事件；跳過靜態資源與敏感登入內容。

## 需求與驗收標準

- 先以預設清單過濾 `工作單` 與 `檢修級別=C1,C2,C3`；唯一且完全相符時直接點開。
- 僅在第一輪總筆數與列數均為 0 時切換「所有記錄」，重新填入相同條件再過濾。
- 第二輪 0 筆時回報找不到；第一輪或第二輪結構異常、非唯一、非完全相符時報錯。
- `115-C1-41264` 走快速路徑，`115-C1-36682` 走回退路徑，兩者仍有正確 JSON。
- 原有基本資料、通報與維修程序欄位不變。

## 實作備註

- 擴充既有 `MaximoEventClient` 以取得 app 載入時已請求的 HTML，不額外 GET。
- 無新增 CLI、資料模型或遷移；回滾為恢復既有先切所有記錄的查詢順序。

## 驗證契約

- 單元／錄製測試：快路徑、零筆回退、最終零筆、結構異常、事件順序。
- 整合測試：原臨時檢修工單完整 JSON 回歸。
- E2E 測試：`115-C1-41264`、`115-C1-36682`。
- 型別檢查／Lint／Build：`compileall`、`pip check`、`git diff --check`；無獨立型別檢查設定。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：沿用輸入驗證與 session，不保存 HAR 或憑證。

## 完成證據

見 `verification/MMIS-032.md`。
