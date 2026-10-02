# AI-Ready 任務卡

## Metadata

- 任務：建立 HTTP-only 查修工單查詢工具
- 上層規格：`ai/artifacts/MMIS HTTP 查修工單查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 查修工單查詢
- 上層 User Story：依通報號讀取 CA 查修工單
- 分軌：後端
- 前置任務：既有 HTTP 登入、Maximo event、通報詳情 reader 均已完成
- 狀態：完成
- 風險等級：高（認證與內網唯讀查詢）
- Agent owner：Codex
- 人工核准者：專案使用者於 2026-10-02 明確要求開發

## 目標與情境包

- 目標：輸入通報號，輸出查修工單十欄 stdout JSON。
- 相關檔案：`fault_notices/reader.py`、`linked_work_orders.py`、`parser.py`、`events.py`、`tools/mmis_development/`、錄製 HAR/DOM。
- 既有模式：thin wrapper → reusable reader → 單一 HTTP session → Maximo event → semantic table parser。
- 假設：表格 `summary=查修工單` 與欄名穩定；動態 id 每次從回應解析。
- 未知事項：未來頁面結構變動；多頁 live 情況未出現在本次錄製。
- 允許變更：相鄰 reader/parser、開發 wrapper、對應測試、開發工具 README、專案地圖及本 Epic 文件。
- 不得觸碰：`.env`、外部錄製、遠端 MMIS 資料、既有 `Prompt.md` 修改。
- 情境預算：讀流程、地圖、相鄰 reader/parser、HAR 最後關鍵事件與 DOM；跳過靜態資源及無關 app。

## 需求與驗證契約

- 精確查詢一筆通報；讀「故障追蹤」中的目標表格所有分頁，只保留中段 `CA` 工單，依工作單去重。
- 先驗證表格十欄與分頁範圍；空欄保留空字串；不因其他表格空白誤判；頁面異常應失敗。
- 指令：`python -m pytest -q`；`python -m compileall -q src tools/mmis_development tests`；`git diff --check`；指定通報唯讀 live 查詢。
- 無資料模型、遷移或遠端寫入；回滾為移除新 reader/wrapper/test，還原 parser 與相鄰文檔。

## 完成證據

- 參見 `verification/MMIS-025.md`。
