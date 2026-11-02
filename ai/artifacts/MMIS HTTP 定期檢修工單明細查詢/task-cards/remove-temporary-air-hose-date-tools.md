# AI-ready 任務卡：移除軔管日期臨時工具

- 目標：依 `TEMPORARY_AIR_HOSE_DATE_TOOLS.md` 移除三個臨時入口、兩個專用活頁簿模組、軟管日期專用 reader 邏輯及其測試，並更新現行文件。
- 使用者行為：保留定期檢修工單明細與單筆最新工單查詢；移除軔管日期及指定 Excel 批次入口。
- 範圍：`tools/mmis_development/`、`src/mmis_connector/periodic_inspection/`、對應測試、架構清單及現行文件。歷史規格與驗證紀錄保持原樣。
- 依據：暫存清單與本次精確呼叫者搜尋。`LatestPeriodicInspectionWorkOrderQuery` 仍由單筆查詢入口使用。
- 非目標：修改 MMIS 連線、既有工單明細輸出、Downloads 活頁簿或歷史產出物。
- 風險：低。刪除本機開發工具；不執行遠端 MMIS 操作，也不讀寫使用者活頁簿。
- 驗收：被刪入口與專用模組不存在；現行文件無失效入口；定期檢修明細、最新工單查詢與架構測試通過；`git diff --check` 通過。
- 驗證：`python -m pytest tests/test_periodic_inspection_work_order_details.py tests/test_query_latest_periodic_inspection_work_order.py tests/test_architecture.py -q`，再跑完整離線測試集。
- 人工核准：使用者本次明確要求刪除與更新 README，並在確認後刪除暫存文件。

## 驗證結果

- `python -m pytest -q -o addopts=''`：542 passed，43 skipped。
- `python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development`：通過。
- `git diff --check`：通過。
- 精確搜尋現行 `src/`、`tools/`、`tests/`、`ai/context/` 與 `docs/development/`：無已刪入口、模組或 Downloads 專用路徑的引用。
- `TEMPORARY_AIR_HOSE_DATE_TOOLS.md` 已刪除；未執行 MMIS Live 查詢，亦未更動 Downloads 活頁簿。
