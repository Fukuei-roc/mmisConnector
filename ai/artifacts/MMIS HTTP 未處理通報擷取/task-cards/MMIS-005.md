# AI-Ready 任務卡

## Metadata

- 任務：建立可擴充的 MMIS 功能模組命名模式
- 上層規格：`feature-spec.md`
- 上層 Epic：MMIS HTTP 未處理通報擷取
- 上層 User Story：查詢並輸出故障通報 JSON
- 分軌：後端
- 前置任務（dependsOn）：MMIS-004
- 狀態：完成（2026-09-21）
- 風險等級：低
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標

將語意過度寬泛的 `workflow.py` 改為能描述具體 MMIS 功能的模組與類別名稱，並記錄後續命名規則。

## 情境包（Context Pack）

- 相關檔案：`workflow.py`、`cli.py`、`__init__.py`、README、架構地圖、任務卡 refs
- 既有模式：一個模組負責一個完整 MMIS 操作；登入與解析器維持共用
- 假設：目前沒有 repo 外部呼叫者依賴舊類別名稱
- 未知事項：無
- 允許變更的檔案：上述引用與新增的命名回歸測試
- 不得觸碰：HTTP event sequence、登入、parser、JSON 契約

## 需求

- 功能模組使用 `動作_領域物件.py`。
- 查詢類別使用 `<DomainObject>Query`；單筆讀取使用 `<DomainObject>Reader`。
- 目前模組改為 `query_unprocessed_fault_notices.py`，類別改為 `UnprocessedFaultNoticeQuery`。
- 更新全部內部引用與 README。

## 驗收標準

- 執行碼與測試不再引用舊模組或舊類別名稱。
- CLI 與 JSON 契約不變。
- 全部測試通過。

## 驗證契約

- 單元測試：新公開類別可匯入。
- 回歸測試：完整 pytest。
- 型別／語法：compileall。
- 靜態檢查：搜尋舊名稱為零。
