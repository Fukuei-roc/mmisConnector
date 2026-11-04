# 刪除未派工的日檢工單

## 情境包與範圍

- 目標：命令列接收一個工作單號，僅在日檢工單明細的「工作單狀態」為「執行中未派工」時執行「工單取消」。
- 既有模式：`DailyInspectionWorkOrderDetailReader.open_detail` 查詢唯一工單；`MaximoEventClient` 發送 Maximo event；development wrapper 輸出 JSON。
- 錄製證據：2026-11-04 的 timeline 顯示查詢、開啟明細、點工單取消、填「重複開單」、點確定與點是。錄製目錄沒有 `raw.har`，完整回應與成功狀態無法離線核對。
- 探索範圍：讀取專案地圖、現有日檢查詢與勾稽程式、錄製摘要和 timeline；未讀無關的故障通報模組。

## 任務契約

- 輸入：一個工作單號，格式沿用現有 `normalize_work_order`。
- 拒絕：明細狀態不符時輸出「非執行中未派工工單不可刪除」，不送取消 event。
- 執行：理由固定為錄製中的「重複開單」，送出確認後重新查詢狀態；狀態須為「工單取消」才回傳成功。
- 非目標：批次處理、實際刪除測試、資料庫刪除、修改既有查詢介面。
- 風險：高。操作會改動 MMIS 工單，回應逾時時結果可能不明，不自動重送。由使用者執行實機驗收。
- 核准狀態：使用者於本次請求明確要求開發，並保留實際刪除測試。

## 驗證與審查

- `python -m pytest tests/test_read_daily_inspection_work_order.py tests/test_link_fault_notice_to_daily_inspection_work_order.py tests/test_cancel_daily_inspection_work_order.py -q`：通過，3 項既有測試略過。
- `git diff --check`：通過。
- 安全檢查：狀態從已開啟明細核對；查詢結果與輸入工作單一致；動作完成後重新讀取狀態；不記錄認證資料。
- 殘留風險：錄製缺 HAR，實機動態對話框結構與成功回應尚待驗收。
