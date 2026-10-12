# AI-Ready 任務卡

## Metadata

- 任務：MMIS-037 日檢檢修記錄輸出檢修人員
- 上層規格：`ai/artifacts/MMIS HTTP 日檢檢修記錄查詢/feature-spec.md` 2026-10-12 擴充
- 上層 Epic：MMIS HTTP 日檢檢修記錄查詢
- 上層 User Story：查詢日檢工單時顯示檢修人員名單
- 分軌：後端
- 前置任務：MMIS-036（done）
- 狀態：完成；使用者於 2026-10-12 明確要求實作
- 風險等級：高（沿用 MMIS 身分驗證與內網唯讀 HTTP）
- Agent owner：Codex
- 人工核准者：專案使用者（功能範圍與輸出順序）

## 目標與情境包

- 目標：在指定 CLI JSON 最下方輸出五欄檢修人員名單。
- 相關檔案：`src/mmis_connector/daily_inspection/reader.py`、指定 development tool、對應測試、指定錄製 HAR 與 DOM。
- 既有模式：單一 Session、Maximo event、動態頁籤定位、摘要與表頭定位表格、分頁完整性檢查、`count`/`records` 契約。
- 假設：錄製的「檢修人員(單位)」頁籤與表格標題仍適用；live 查詢已確認。
- 未知事項：其他工單可能有多頁或空表；以既有分頁模式處理並測試。
- 允許變更：日檢 reader、指定 tool／測試、本 Epic 規格與任務證據、看板卡片。
- 不得觸碰：`.env`、外部錄製、登入流程、其他 domain、UI。
- 情境預算：閱讀流程、地圖、reader/tool/test、錄製摘要、HAR 目標 event 與最終 DOM；略過靜態流量及其他功能。

## 需求與驗收標準

- 新群組為最後一個頂層 JSON 鍵；每筆只保留人員群組、工作角色、員工代號、姓名、單位，順序與畫面一致。
- 指定錄製和 live 工單 `115-1A-71815` 均取得 7 筆；空表為零筆，表格缺失或分頁不完整時安全失敗。
- 既有欄位及查詢行為維持正常。

## 實作與驗證契約

- API：單一工單號輸入，新增頂層「檢修人員」物件；無遷移。
- 錯誤與安全：沿用原 Session、工單號驗證及 `MMISClientError`；不落盤人員資料、憑證或原始回應。
- 回滾：移除頁籤查詢與新增 JSON 鍵即可。
- 測試：錄製 7 筆、跨頁、缺表／不完整分頁、JSON 順序、完整回歸與 live 唯讀 CLI。
- Lint／Build：`git diff --check`、`python -m compileall -q src tools/mmis_development tests`。
- 螢幕截圖：不適用，CLI 無 UI 變更；以錄製 DOM、HAR 及 live JSON 驗證。
- 審查：架構、安全性、測試及 code review；確認無新增寫入 event 或敏感資料落盤。

## 完成證據

見 `verification/MMIS-037.md`。
