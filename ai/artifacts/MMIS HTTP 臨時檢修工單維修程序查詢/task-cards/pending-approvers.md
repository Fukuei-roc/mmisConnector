# AI-Ready 任務卡：臨時檢修工單待簽核人

## Metadata

- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 分軌：後端
- 前置任務：無
- 狀態：完成
- 風險等級：中，沿用既有唯讀 HTTP session
- 人工核准者：使用者於 2026-10-30 明確要求實作

## 目標與情境包

- 目標：在指定 CLI 的 JSON 中加入可供姓名成員查詢的 `待簽核人` 陣列。
- 相關檔案：`src/mmis_connector/temporary_repair/reader.py`、`tests/test_temporary_repair_procedure.py`、CLI wrapper。
- 既有模式：Reader 使用 `MaximoEventClient` 切換頁簽，並用共用 parser 檢查表格與分頁。
- 假設：錄製中的「核簽記錄」是使用者所稱「簽核記錄」；已由實際頁簽標題確認。
- 未知事項：無。
- 允許變更：本規格、任務卡、Reader、對應測試與驗證報告。
- 不得觸碰：認證、其他查詢、錄製原始資料。
- 情境預算：只讀專案地圖、相關 Reader 與測試、錄製摘要和核簽頁的 HAR/DOM；未掃描其他 MMIS app。

## 驗收標準

- `核簽中`：讀取全部核簽流程分頁，收集所有 `目前進行者` 的非空姓名，去重排序。
- 其他狀態：輸出 `[]`，且不查詢核簽頁。
- JSON 順序為 `工作單狀態`、`待簽核人`、`已勾稽故障通報`。
- 表格或分頁異常時報錯，不輸出不完整姓名。

## 驗證契約

- 離線：新錄製 HAR 的 5 筆中取得 4 位目前進行者；測試核簽頁切換、非核簽中空值與欄位順序。
- 即時：執行指定 CLI，確認姓名、狀態與 JSON 順序；另查非核簽中工單。
- 全套：`python -m pytest -q`、`python -m compileall -q src tools`、`git diff --check`。
- UI 螢幕截圖：不適用，只有 CLI JSON 輸出。
