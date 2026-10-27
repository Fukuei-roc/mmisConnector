# AI-Ready 任務卡

## Metadata

- 任務：批次回填與錯誤後接續處理
- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS 定期檢修工單 Excel 回填
- 上層 User Story：批次回填、錯誤後接續
- 分軌：後端
- 前置任務：既有最新定期檢修工單查詢（已完成）
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：使用者於 2026-10-27 直接要求實作及錯誤後接續處理

## 目標與範圍

提供可重跑的批次指令，讀取指定 Excel 的車號，查詢並回填三欄。允許變更 `src/mmis_connector/periodic_inspection/`、`tools/mmis_development/`、相關測試與本 Epic 產出物。不得改動 MMIS 查詢的既有篩選條件。

## 情境包

- 既有查詢：`src/mmis_connector/periodic_inspection/query.py` 的 `LatestPeriodicInspectionWorkOrderQuery` 回傳四欄字典。
- CLI 模式：`tools/mmis_development/query_latest_periodic_inspection_work_order.py`。
- Excel 模式：`tools/mmis_development/_unclosed_ab_xlsx.py` 使用 openpyxl。
- 風險：外部檔案覆寫、MMIS 認證與網路、錯誤後的部分完成狀態。
- 驗證：暫存活頁簿及假查詢；實際檔案讀回；相關測試與架構檢查。
- 情境預算：已讀上述模組、專案地圖、實際檔案的標題與筆數；略過不相關的 UI 與故障通報流程。

## API 與資料契約

- 指令預設處理 `C:\Users\NMMIS\Downloads\軔管日期統計\配屬車號總表.xlsx`，允許指定 `--workbook`。
- A 至 D 欄標題固定且依序為「車組/車號」、「檢修級別」、「工作單」、「檢修日期」。
- 成功列的 B 至 D 欄均為文字；失敗列保留原值。完整列跳過，未完成列重查。
- 單列查詢錯誤以新連線最多嘗試三次，仍失敗不終止整批；檔案結構或寫入錯誤終止整批。摘要不得含敏感資訊。

## 驗證契約

- 測試：檔案預檢、成功回填、重試成功、重試耗盡後續處理、重跑、暫存檔替換失敗與文字儲存。
- 指令：`python -m pytest tests/test_periodic_inspection_workbook.py tests/test_architecture.py -q`。
- 審查：架構、安全性與測試策略；實際檔案操作後讀回比對。
- 回滾：每筆成功即有原檔進度。需回滾時以執行前備份還原，不自動清除已完成列。

## 完成證據

- 變更的檔案：`src/mmis_connector/periodic_inspection/workbook.py`、`tools/mmis_development/fill_latest_periodic_inspection_work_orders.py`、`tools/mmis_development/README.md`、相關測試。
- 執行過的指令與輸出：見 `../verification/batch-fill.md`。
- 已知限制：不可同時由 Excel 或另一個程序編輯同一檔案。
- 後續任務：無。
