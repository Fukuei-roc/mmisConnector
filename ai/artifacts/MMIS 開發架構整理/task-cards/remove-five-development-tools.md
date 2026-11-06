# AI-ready 任務卡：刪除五個重複查詢入口

## Metadata

- 任務：刪除已由完整查詢涵蓋的五個單項開發入口。
- 上層 Epic：MMIS 開發架構整理。
- 上層規格：使用者本次明確指定刪除；前置準備見 `prepare-remove-five-development-tools.md`。
- 分軌：後端。
- 前置任務：準備移除五個重複查詢入口，已完成。
- 狀態：完成。
- 風險等級：低。只刪本機開發入口，不更動正式元件或 MMIS 資料。
- 人工核准者：使用者本次訊息。

## 目標與範圍

刪除下列五個檔案，並確認 `tools/mmis_development/README.md` 不再列出其指令：

- `query_fault_notice_analysis.py`
- `query_atp_fault_analysis_linked_to_fault_notice.py`
- `query_work_orders_linked_to_fault_notice.py`
- `query_repair_work_orders_linked_to_fault_notice.py`
- `query_daily_inspection_work_order_by_number.py`

允許變更上述五個入口、開發工具 README、對應架構測試與本任務的驗證報告。不變更 `src/mmis_connector/`、歷史規格與已完成看板卡片。

## 情境包

- 既有模式：正式功能位於 `src/mmis_connector/`。完整通報入口包含四項故障通報資料；日檢完整明細入口包含已勾稽通報。
- 依賴狀態：前置任務已移除現行程式、測試與指令文件對五個入口的引用。完整測試在阻擋五個模組 import 後通過。
- 未知事項：repo 以外的排程或人工腳本無法由本次測試確認。

## 驗收標準與驗證契約

- 五個檔案不存在，開發工具 README 無五個指令。
- 現行程式、測試與指令文件無五個模組的精確引用。
- `tests/test_architecture.py`、完整通報與日檢明細測試通過。
- 完整離線測試通過；`git diff --check` 通過。
- 不執行 MMIS Live 操作，不產生 UI 截圖。

## 完成證據

- 五個入口均不存在；目錄剩 17 個可執行工具。
- 現行程式、測試與指令文件對五個模組的精確引用為 0。
- 定向測試 51 passed、7 skipped；完整離線測試 604 passed、48 skipped。
- 證據詳見 `../verification/remove-five-development-tools.md`。
