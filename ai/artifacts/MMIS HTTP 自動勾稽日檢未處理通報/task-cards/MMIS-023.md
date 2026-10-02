# AI-Ready 任務卡

## Metadata

- 任務：修正勾稽後指定故障通報的確認誤判
- 上層規格：`ai/artifacts/MMIS HTTP 自動勾稽日檢未處理通報/feature-spec.md`
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：尋找日檢工單與自動勾稽
- 分軌：後端
- 前置任務（dependsOn）：無
- 狀態：完成（待人工驗收）
- 風險等級：高（MMIS 遠端寫入後的確認）
- Agent owner：Codex
- 人工核准者：專案使用者於 2026-10-02 明確要求修正現有確認功能

## 目標

以重新讀取指定日檢工單的「故障通報管理」表格確認勾稽，正確解析通報號輸入框的 `value`。

## 情境包（Context Pack）

- 相關檔案：`daily_inspection/linker.py`、`parser.py`、對應測試；唯讀參考 2026-10-02 Recorder 的 HAR/DOM 與現有 SQLite。
- 既有模式：單一 HTTP session、精確工作單查詢、表格標題與欄名定位、寫入 POST 不重試。
- 假設：重讀的工單明細反映 MMIS 已保存的資料。
- 未知事項：未在線上 MMIS 執行新版勾稽；本地錄製只涵蓋確認查詢。
- 允許變更的檔案：本卡、linker、parser、對應測試及驗證報告。
- 不得觸碰：SQLite 既有狀態、CLI 契約、錄製原始檔、`Prompt.md`。
- 情境預算備註：讀取專案地圖、相關 domain 模組與測試、錄製中的關鍵事件與 DOM；未逐頁檢查無關靜態資源。

## 需求

- 寫入 POST 只送一次；不以寫入回應的局部畫面直接判定成功。
- 重新開啟同一工單，只接受完全相同的工作單號及故障通報號。
- 表格解析應支援 Maximo 在 `<input value>` 呈現故障通報號。
- 確認失敗保持既有 `link_error` 與不自動重送語意。

## 驗收標準

- 2026-10-02 錄製明細可解析出 `1150929-07`、`1150929-10`。
- 寫入回應不含表格但重新查詢含指定通報時成功。
- 重新查詢缺少指定通報或工作單不符時拒絕確認。
- 寫入失敗不再查詢，且不重送。

## 實作備註

- 使用既有 `DailyInspectionWorkOrderDetailReader.open_detail()`，不新增 HTTP 協定層。
- 只改確認路徑；不更新資料庫既有 `link_error` 記錄。

## 驗證契約

- 單元測試：input value、重讀成功與失敗、工作單不符、寫入不重送。
- 整合測試：既有自動勾稽與日檢工單測試。
- E2E 測試：本卡不執行線上寫入；離線用 Recorder HAR/DOM 核對。
- 型別檢查：專案未配置。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tests`。
- 螢幕截圖：無 UI 變更；錄製 DOM 是驗證依據。
- 安全性檢查：不新增憑證儲存、不重送寫入、不輸出 HAR 中的 token。

## 完成證據

- 詳見 `verification/MMIS-023.md`。
