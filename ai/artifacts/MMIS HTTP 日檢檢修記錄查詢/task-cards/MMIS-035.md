# AI-Ready 任務卡

## Metadata

- 任務：MMIS-035 日檢檢修記錄查詢新增七欄基本資料
- 上層規格：`ai/artifacts/MMIS HTTP 日檢檢修記錄查詢/feature-spec.md` 2026-10-12 擴充
- 上層 Epic：MMIS HTTP 日檢檢修記錄查詢
- 上層 User Story：查詢工單時同時取得基本資料
- 分軌：後端
- 前置任務：MMIS-023（done）
- 狀態：完成；使用者於 2026-10-12 明確指定實作與欄位順序
- 風險等級：高（既有 MMIS 身分驗證與內網唯讀 HTTP）
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標與情境包

- 目標：成功 JSON 頂部依指定順序輸出七個工單基本欄位。
- 相關檔案：`src/mmis_connector/daily_inspection/reader.py`、對應 development tool、測試、2026-10-12 指定錄製 DOM。
- 既有模式：`open_detail()` 唯一命中；標籤／`for` 擷取；日期空 `value` 時讀 `title` 或台北時間 `dojovalue`；薄 CLI wrapper。
- 假設：基本資料位於既有明細回應，不需新增 HTTP event。
- 未知事項：其他工單的同名欄位可能重複；值衝突時拒絕輸出。
- 允許變更：日檢 reader、對應 tool／測試／說明與本 Epic artifacts。
- 不得觸碰：工單篩選和唯一命中邏輯、`.env`、外部錄製、其他 domain 與 UI。
- 情境預算：讀取專案地圖、流程、指定 reader/tool/test、既有基本資料解析器、錄製摘要及 DOM；未讀無關 MMIS 流量。

## 需求與驗收標準

- 七欄在第一層最前面依使用者順序排列，後續既有 JSON 結構保留。
- 日期正確顯示 `YYYY/MM/DD`；開單日期為 `YYYY/MM/DD HH:mm`。
- 缺欄、重複衝突或工作單不相符時回傳 `MMISClientError`。
- 錄製 DOM、單元測試和指定 live 唯讀查詢驗證。

## 實作與驗證契約

- API：單一工單號輸入；成功 JSON 新增七個頂層字串欄位；無資料庫遷移。
- 身分驗證、權限及錯誤：重用現有 Session 和錯誤處理；不輸出原始回應或憑證。
- 回滾：移除擷取函式及七欄輸出，既有 `open_detail()` 不需改動。
- 測試：錄製 DOM、Dojo 日期與時間、工單不符、重複標籤、原有分頁及 JSON 順序。
- E2E：執行使用者指定的唯讀 CLI。
- Lint／Build：`git diff --check`、`python -m compileall -q src tools/mmis_development tests`；無獨立 typecheck。
- UI 截圖：不適用；本任務無 UI 變更。
- 審查關卡：架構、安全性、測試與 code review；確認無新增網路請求、敏感常值或找工單邏輯變更。

## 使用者後續修訂

- 2026-10-12：最前面三鍵改為 `query_name`、`query_work_order_number`、`success`，接續七欄基本資料；移除本 CLI 輸出的 `work_order` 鍵。
- 變更範圍限於 development tool 的 JSON 包裝、對應測試與說明；domain reader 的輸入參數及找工單流程維持原樣。

## 完成證據

見 `verification/MMIS-035.md`。
