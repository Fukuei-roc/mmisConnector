# 任務卡 MMIS-BATCH-APPROVAL-EXECUTE

- 上層規格：`ai/artifacts/自動批次核簽/feature-spec.md`。
- 狀態：已完成實際寫入驗收。使用者於 2026-11-16 明確授權真實核簽及有限測試。
- 前置任務：`MMIS-BATCH-APPROVAL-COUNTS`，讀取功能已有驗證證據。
- 範圍：`src/mmis_connector/batch_approval.py`、`tools/mmis_development/auto_batch_approve.py`、對應測試與本 Epic 文件。
- 資料契約：stdout 為 17 類已簽核數 JSON，值為非負整數；錯誤時非零結束，不輸出成功 JSON。
- 不新增 UI、資料模型、環境變數或持久化資料。沿用副段長帳號及同源 HTTP session。
- 驗收：零待簽時全零輸出且不發核簽事件；有待簽時每輪四事件，依 MMIS 對話框累計已核簽數；異常回應停止。
- 風險：高。網路與核簽寫入不可回滾；以逐輪重新讀取及不自動重試 POST 控制重送風險。
- 驗證：錄製 HAR 比對事件形狀、單元測試、全套 pytest、實際零待簽 CLI。
