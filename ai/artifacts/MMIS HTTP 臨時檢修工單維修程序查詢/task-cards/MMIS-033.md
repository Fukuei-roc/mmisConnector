# AI-Ready 任務卡

## Metadata

- 任務：臨時檢修工單明細查詢指令更名
- 上層規格：`ai/artifacts/MMIS HTTP 臨時檢修工單維修程序查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 上層 User Story：依工作單號查詢完整工單明細
- 分軌：後端文件與 CLI 入口
- 前置任務（dependsOn）：MMIS-032 已實作
- 狀態：完成；使用者已明確核准本次更名
- 風險等級：低；唯讀查詢邏輯維持原樣
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-07 明確要求更名）

## 目標

將開發指令與輸出名稱改為「查詢臨時檢修工單明細」，README 清楚列出輸入與所有輸出欄位。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/` 的原 wrapper 與 README、`src/mmis_connector/temporary_repair/reader.py`、`tests/test_temporary_repair_procedure.py`、`ai/context/project-map.md`。
- 既有模式：薄 wrapper 建立 `MMISSession` 和 reader；reader 組裝 JSON，`run_json_tool` 處理錯誤。
- 假設：英文模組名稱採 `query_temporary_repair_work_order_detail`，其語意與指定中文名稱一致。
- 未知事項：Live MMIS 是否可連線；用離線測試與 CLI 參數測試驗證可執行性。
- 允許變更的檔案：上述 wrapper、README、reader、測試、project map、本卡與驗證報告。
- 不得觸碰：認證與查詢流程、HAR、`.env`、其他工具。
- 情境預算備註：只讀專案地圖、流程、指定工具與測試，跳過無關 domain 與敏感錄製。

## 需求與驗收標準

- 新模組指令可透過 `python -m` 執行；舊名不再作為正式指令。
- 成功輸出的 `query_name` 是「查詢臨時檢修工單明細」，其他資料鍵與值保持原契約。
- README 用途說明輸入一個工作單號，列出頂層基本資料、已勾稽故障通報與維修程序概況的全部欄位。
- 對應測試匯入新模組，檢查新用法與輸出名稱。

## 實作備註

- 只更名 wrapper 與顯示名稱，不更動 `TemporaryRepairProcedureReader` 類別或查詢事件。
- 不涉及資料模型與遷移；若需回滾，還原 wrapper 檔名、名稱常數與文件。

## 驗證契約

- 單元測試：`python -m pytest tests/test_temporary_repair_procedure.py -q`。
- CLI 測試：新模組缺少參數時顯示新用法並以 1 結束。
- 靜態檢查：`python -m compileall -q src/mmis_connector/temporary_repair tools/mmis_development tests/test_temporary_repair_procedure.py`、`git diff --check`。
- UI 螢幕截圖：不適用。
- 安全性檢查：不改認證、網路或資料寫入路徑。

## 完成證據

見 `verification/MMIS-033.md`。
