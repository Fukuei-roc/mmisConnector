# AI-Ready 任務卡

## Metadata

- 任務：完整故障通報輸出 ATP 故障分析未填妥狀態
- 上層規格：使用者於 2026-10-16 提供的三種判定規則與欄位順序
- 上層 Epic：MMIS HTTP 故障通報整合查詢
- 上層 User Story：查詢故障通報結案狀態
- 分軌：後端
- 前置任務：既有完整故障通報查詢及結案狀態檢查
- 狀態：使用者已核准實作
- 風險等級：低（僅讀取既有 JSON，不增加網路事件）
- Agent owner：Codex
- 人工核准者：使用者於本次訊息直接要求新增欄位

## 目標與契約

在 `結案狀態檢查` 內，緊接 `CA Repair Work Orders Not Closed` 輸出布林欄位 `ATP Fault Analysis Incomplete`。`是ATP故障` 為 `false` 時輸出 `false`；為 `true` 時，`ATP故障分析` 的 `故障要因`、`故障因子`、`故障項目` 任一為空或純空白就輸出 `true`，三欄均有內容則輸出 `false`。

## 情境包

- 相關檔案：`tools/mmis_development/query_fault_notice_full_detail.py`、`src/mmis_connector/fault_notices/full_detail.py`、`tests/test_depot_work_order_status.py`、`tests/test_fault_notice_analysis_materials.py`。
- 既有模式：完整查詢 reader 一次讀取 ATP 標記和三欄，wrapper 依序組裝 `結案狀態檢查`，空欄由 parser 保留空字串。
- 假設：缺失或 `null` 的 ATP 分析欄位視為空；欄位名稱使用 `ATP Fault Analysis Incomplete`。
- 未知事項：無。
- 允許變更：完整查詢 wrapper、相關測試及本 Epic 的任務與驗證紀錄。
- 非目標：改動 MMIS 讀取、認證、其他查詢命令及遠端資料。
- 風險區域：JSON 欄位順序與既有消費端契約。
- 驗證指令：`python -m pytest tests/test_depot_work_order_status.py tests/test_fault_notice_analysis_materials.py -q`、`git diff --check`。
- 情境預算備註：讀取專案地圖、流程、完整查詢 wrapper/reader、ATP 欄位定義及兩個相關測試；未讀敏感錄製資料或全專案原始碼。

## 驗收標準

- 三種指定情境均輸出正確布林值；三欄每一欄單獨為空均受測。
- 欄位位置緊接 `CA Repair Work Orders Not Closed`。
- 原始 reader 輸出不被修改，且不增加 MMIS 網路事件。
