# AI-Ready 任務卡

## Metadata

- 任務：建立 HTTP-only 故障通報關聯工單查詢工具
- 上層規格：`ai/artifacts/MMIS HTTP 故障通報關聯工單查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 故障通報關聯工單查詢
- 上層 User Story：依通報號讀取關聯工單
- 分軌：後端
- 前置任務：既有 HTTP 登入、Maximo event、故障通報詳情 reader 均已完成
- 狀態：完成
- 風險等級：高（認證及內部網路唯讀存取）
- Agent owner：Codex
- 人工核准者：專案使用者於 2026-10-02 明確要求開發

## 情境包

- 相關檔案：`fault_notices/reader.py`、`parser.py`、`events.py`、`tools/mmis_development/`、錄製 HAR/DOM。
- 既有模式：thin development wrapper → reusable reader → HTTP session/event/parser。
- 假設：錄製的「故障追蹤」頁籤及表格語意標籤維持一致；動態 id 每次解析。
- 未知事項：其他通報的最大分頁量與未來 DOM 變化。
- 允許變更：上述相鄰實作、測試、開發工具 README、本 Epic 文件。
- 不得觸碰：`.env`、外部錄製、MMIS 遠端資料、使用者既有 `Prompt.md` 修改。
- 情境預算：讀專案地圖、流程、相鄰 reader/parser、錄製摘要及關鍵 HAR event/DOM；略過無關 app 與靜態資源。

## 需求與驗證契約

- 精確查詢一筆通報，讀取故障追蹤的「檢視所有段檢修工單」表格全部分頁。
- 精確篩選的故障通報必須吻合輸入；關聯表七欄必須齊全，工單列通報號保留 MMIS 原值（併單時可不同）；工作單不得空白，依工作單去重。
- 測試：`python -m pytest -q`；live：指定通報唯讀查詢；建置：`python -m compileall -q src tests tools/mmis_development`；檢查：`git diff --check`。
- 無資料遷移；回滾為移除新增 wrapper/reader 並還原相鄰 parser/reader 改動。

## 完成證據

- 參見 `verification/MMIS-024.md`。
