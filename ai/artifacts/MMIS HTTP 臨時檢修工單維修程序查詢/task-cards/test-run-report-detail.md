# AI-Ready 任務卡：試車子單明細

## Metadata

- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 分軌：後端
- 前置任務：無
- 狀態：完成
- 風險等級：中，沿用既有唯讀 HTTP session
- 人工核准者：使用者於 2026-10-30 指定 TR JSON 欄位與錄製檔

## 目標與情境包

- 目標：輸入三位數尾碼的 TR 試車子單時，CLI 輸出指定的 12 個 JSON 鍵。
- 相關檔案：`src/mmis_connector/temporary_repair/reader.py`、`tests/test_temporary_repair_procedure.py`、本 Epic 規格。
- 既有模式：Reader 先依工作單與檢修級別唯一篩選，再以動態頁簽 ID 和共用表格 parser 讀取明細。
- 已確認：錄製 HAR 的入口、試車結果、關聯工單、核簽記錄回應依序為 344、349、353、357；關聯工單同時含子單與母單狀態。
- 假設：`query_name` 沿用既有 CLI 名稱；日期使用台北時區。
- 未知事項：無。
- 允許變更：Reader、對應測試、本規格、任務卡與驗證報告。
- 不得觸碰：認證、其他查詢、原始 HAR、一般工單 JSON 契約。
- 情境預算：只讀專案地圖、相關 Reader/測試、錄製摘要與四個相關 HAR/DOM 回應；未掃描其他 app。

## 驗收標準

- TR 尾碼工單以 `TR` 過濾；一般工單仍以 `C1,C2,C3` 過濾。
- TR JSON 僅有規格列出的 12 個鍵，順序正確，工作單與輸入完全相符。
- 工作單狀態按子單號取得；待簽核人沿用目前進行者規則；試車日期可從 `dojovalue` 取得。
- 多筆 TR 結果輸出 `查找到多筆試車報告`；一般工單查詢與輸出不變。

## 驗證契約

- 離線：錄製 HAR 重放四個頁簽，檢查完整 JSON；聚焦測試過濾條件與多筆錯誤。
- 即時：執行指定 TR CLI，並檢查一般工單原格式。
- 全套：`python -m pytest -q`、`python -m compileall -q src tools`、`git diff --check`。
- UI 螢幕截圖：不適用，只有 CLI JSON 輸出。

## 完成證據

- 變更檔案：Reader、對應測試、本規格、任務卡與驗證報告。
- 執行指令與結果：見 `../verification/test-run-report-detail.md`。
- 已知限制：錄製範例的核簽流程只有一頁；跨頁沿用既有分頁檢查。
