# 任務卡 MMIS-BATCH-APPROVAL-OUTPUT

- 上層規格：`ai/artifacts/自動批次核簽/feature-spec.md`。
- 目標：讓代理副段長在 CLI 中看到核簽前、核簽後與最後複查的數量。
- 狀態：實作與驗證完成。使用者明確要求修改並驗證此指令。
- 前置任務：`MMIS-BATCH-APPROVAL-EXECUTE` 已完成。
- 風險等級：高。指令沿用既有 MMIS 寫入，核簽不能自動回滾。

## 情境包與範圍

- 相關檔案：`tools/mmis_development/auto_batch_approve.py`、`tools/mmis_development/_support.py`、`src/mmis_connector/batch_approval.py`、對應測試與本 Epic 文件。
- 既有模式：副段長專用登入、`query_pending_counts`、`approve_all_pending` 與 `run_json_tool` 的安全 JSON 錯誤輸出。
- 假設：全部 17 類的前後待簽數都顯示；已簽核數只顯示非零類別；三段輸出均為 JSON 物件。
- 未知事項：核簽時可能有新工單加入，因此最後須重新查詢，不能用初始數減已簽數推算。
- 允許變更：CLI、CLI 輸出測試、開發工具 README 與本 Epic 產出物。
- 不碰：共用核簽事件流程、登入實作、其他工具及範本。
- 情境預算：讀取專案地圖、流程、現有 CLI、輸出共用函式與核簽模組；未擴查其他 MMIS 功能。

## 驗收契約

- 核簽前立即輸出完整 17 類待簽數量。
- 核簽結束後只輸出本次非零已簽核類別。全零時輸出空物件。
- 最後獨立查詢完整 17 類待簽數並回報是否全零。任一類非零時非零結束，仍顯示複查數量。
- 輸出不含憑證、cookie 或工單個資；保留既有例外的安全 JSON 格式。
- 驗證：CLI 輸出測試、`python -m pytest -q`、實際 CLI 與 `git diff --check`。
