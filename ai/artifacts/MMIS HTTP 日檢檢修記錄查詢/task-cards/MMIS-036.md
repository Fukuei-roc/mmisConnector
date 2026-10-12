# AI-Ready 任務卡

## Metadata

- 任務：MMIS-036 日檢檢修記錄輸出已勾稽故障通報
- 上層規格：`ai/artifacts/MMIS HTTP 日檢檢修記錄查詢/feature-spec.md` 2026-10-12 擴充
- 上層 Epic：MMIS HTTP 日檢檢修記錄查詢
- 上層 User Story：查詢工單時同時取得已勾稽故障通報
- 分軌：後端
- 前置任務：MMIS-035（done）
- 狀態：完成；使用者於 2026-10-12 明確要求實作及輸出順序
- 風險等級：高（沿用 MMIS 身分驗證與內網唯讀 HTTP）
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標與情境包

- 目標：在指定 CLI JSON 的開單日期與檢修記錄之間輸出已勾稽故障通報。
- 相關檔案：日檢 reader、對應 development tool、測試、指定錄製 DOM、臨修 reader。
- 既有模式：`open_detail()` 取得唯一工單明細；依表格摘要與四個表頭解析；臨修採 `count`/`records` 格式。
- 假設：故障通報管理在既有明細回應內；錄製與 live 查詢已確認。
- 未知事項：多頁通報缺乏錄製證據，維持安全錯誤。
- 允許變更：日檢 reader、對應 tool／測試、本 Epic artifacts 與看板卡片。
- 不得觸碰：`.env`、外部錄製、工單篩選、其他 domain、UI。
- 情境預算：讀取流程、地圖、指定 reader/tool/test、臨修通報解析、錄製摘要及目標 DOM；略過靜態流量與無關 MMIS 功能。

## 需求與驗收標準

- 四欄資料以 `{"count": n, "records": [...]}` 輸出；空表輸出 0 筆。
- 表格缺失或分頁不完整時回傳錯誤，不回傳部分結果。
- 新鍵位於開單日期之後、檢修記錄之前；既有群組和工單查詢不變。
- 指定錄製與 live 工單讀到 `1151006-32`。

## 實作與驗證契約

- API：單一工作單號輸入；成功 JSON 新增一個頂層物件，無資料庫遷移。
- 身分驗證與錯誤：重用原 Session、既有輸入驗證及 `MMISClientError`；不記錄憑證或原始回應。
- 回滾：移除新增解析與 JSON 欄位，工單開啟流程不變。
- 測試：空表、錄製 DOM、分頁不完整、JSON 順序、原有回歸測試與 live 唯讀 CLI。
- Lint／Build：`git diff --check`、`python -m compileall -q src tools/mmis_development tests`。
- 螢幕截圖：不適用，CLI 無 UI 變更。
- 審查：架構、安全性、測試與 code review，確認無新增網路事件與敏感資料落盤。

## 完成證據

見 `verification/MMIS-036.md`。
