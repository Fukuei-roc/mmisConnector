# AI-Ready 任務卡

## Metadata

- 任務：實作未送簽核日檢工單唯讀查詢
- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢
- 上層 User Story：內部使用者一次取得所有符合條件的工單
- 分軌：後端
- 前置任務：無
- 狀態：審查中
- 風險等級：高，因 MMIS 網路與身分驗證邊界
- 人工核准狀態：使用者於 2026-11-02 明確要求「先理解現有架構，再實作與驗證」

## 情境包

- 相關檔案：`src/mmis_connector/daily_inspection/query.py`、`src/mmis_connector/parser.py`、`src/mmis_connector/fault_notices/linked_work_orders.py`、`tools/mmis_development/_support.py`、2026-11-02 錄製 DOM 與 workflow。
- 既有模式：`MMISSession` 登入、`MaximoEventClient` 送 event、動態 table prefix、`parse_maximo_page_info` 讀下一頁、`run_json_tool` 輸出。
- 風險區域：分頁漏資料、MMIS 欄位名稱變動、日期時區、session 過期。
- 假設：畫面記錄的三個過濾條件即「未送簽核」的業務定義。
- 未知事項：錄製資料只有 1 筆，沒有真實的多頁回應。
- 情境預算：閱讀 1A 查詢、共用 parser、關聯工單分頁與錄製的 DOM/workflow；跳過無關的故障分析與寫入流程。
- 允許變更：新的查詢元件與 development wrapper、相關測試、架構清單、工具說明及本 Epic 產出物。
- 不得觸碰：MMIS 寫入流程、其他查詢行為、憑證檔。

## 驗證契約

- 錄製 DOM 測試、一頁與 31 筆跨頁測試、失敗分頁測試。
- 執行 `python -m pytest -q` 與實際唯讀 CLI 查詢。
- 無 UI，故不需要螢幕截圖。無獨立 lint、型別檢查或 build 設定。
- 不完整分頁必須失敗，不能回傳部分成功。
