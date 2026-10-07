# AI-Ready 任務卡

## Metadata

- 任務：臨時檢修工單明細新增試車報告
- 上層規格：`ai/artifacts/MMIS HTTP 臨時檢修工單維修程序查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 上層 User Story：依工作單號查詢完整工單明細
- 分軌：後端
- 前置任務（dependsOn）：MMIS-033 已完成
- 狀態：完成；使用者於 2026-10-07 明確指定錄製資料、六個欄位與 JSON 位置
- 風險等級：中；既有 HTTPS 唯讀 session 上增加子項分頁事件
- Agent owner：Codex
- 人工核准者：專案使用者（本次需求）

## 目標

在既有查詢結果最後加入試車報告，保留原本找工單流程。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/temporary_repair/reader.py`、對應測試、development tool README、功能規格與專案地圖。
- 既有模式：`MaximoEventClient` 重用 session；表頭與 summary 定位動態表格；`parse_maximo_page_info` 驗證分頁。
- 假設：「顯示為空」沿用既有清單契約 `{"count": 0, "records": []}`。
- 未知事項：單一工單的子項超過一頁時，MMIS 可能變更 tab 回應內容；以分頁一致性檢查防止部分結果。
- 允許變更的檔案：reader、對應測試、README、專案地圖、本 Epic 的功能規格、任務卡與驗證報告。
- 不得觸碰：工單搜尋與 fallback 邏輯、認證、共用 transport、錄製 HAR、其他 domain。
- 情境預算備註：讀專案地圖、流程、單一 reader 和測試、指定錄製摘要與 HAR 的相關回應；跳過無關功能。

## 需求與驗收標準

- JSON 最後為 `試車報告`，其中 `count` 與 `records` 一致。
- 只收錄檢修內容等於「試車報告」的子項，逐筆保留指定六欄；多筆與多頁均可擷取。
- 沒有試車報告是成功結果，回傳 `{"count": 0, "records": []}`。
- 子項表格或分頁結構異常時回報錯誤，不混入其他子單。
- 原本工單查找事件與條件不變。

## 實作備註

- 在既有「檢修回報」tab 回應中解析「工作單的子項」；必要時按子項表格下一頁。
- 不改資料模型或 MMIS 遠端資料；回滾可移除本欄位與對應 parser。

## 驗證契約

- 單元與錄製：`python -m pytest tests/test_temporary_repair_procedure.py -q`。
- 即時：指定 `115-C2-41283` 應回傳一筆；`115-C2-41266` 應回傳空清單。
- 全套：`python -m pytest -q`、`python -m compileall -q src/mmis_connector/temporary_repair tools/mmis_development tests/test_temporary_repair_procedure.py`、`git diff --check`。
- UI 螢幕截圖：不適用，CLI 輸出；已檢查使用者提供的 DOM 與 HAR。
- 安全性檢查：僅送出既有唯讀表格分頁 click，不保存錄製中的 session 或 token。

## 完成證據

見 `verification/MMIS-034.md`。
