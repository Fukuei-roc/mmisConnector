# AI-Ready 任務卡

## Metadata

- 任務：修正段修工單待簽核狀態判斷。
- 上層規格：使用者本次回報 `1151006-32` 應輸出 `Depot Maintenance Work Orders Pending Approval = true`。
- 上層 Epic：MMIS HTTP 故障通報整合查詢。
- 上層 User Story：正確呈現故障通報的結案狀態檢查。
- 分軌：後端。
- 前置任務：既有完整故障通報查詢，已完成。
- 狀態：完成。
- 風險等級：中。此欄位供後續 SQLite 與 Excel 流程使用。
- Agent owner：Codex。
- 人工核准者：使用者於本次訊息明確要求修復。

## 目標

`1151006-32` 的段修工單含「核簽中」時，完整通報 JSON 的待簽核檢查為 `true`。

## 情境包

- 相關檔案：`tools/mmis_development/query_fault_notice_full_detail.py`、`src/mmis_connector/fault_notices/linked_work_orders.py`、`tests/test_depot_work_order_status.py`。
- 既有模式：Reader 讀取「段修工單」的「工作單狀態」；Development Tool 對這些狀態做布林判斷。
- 假設：MMIS 實際回傳的「核簽中」與既有測試使用的「簽核中」皆應視為待簽核。
- 未知事項：無。既有 SQLite 歷史資料不會自動重算，本卡不處理。
- 允許變更的檔案：上述 Development Tool、目標測試、本卡及對應驗證報告。
- 不得觸碰：MMIS 登入、網路事件、Reader、下游 SQLite 與 Excel 實作。
- 情境預算備註：已讀專案地圖、流程、目標 Reader、判斷函式、測試及相關下游欄位定義，未讀無關模組。

## 需求與驗收標準

- 任一段修工單的「工作單狀態」為「核簽中」時，`Depot Maintenance Work Orders Pending Approval` 為 `true`。
- 既有「簽核中」案例維持 `true`，其他狀態與空清單維持原判斷。
- `1151006-32` 的即時查詢輸出該欄為 `true`。
- 非目標：修改「狀態」欄、CA 工單規則、歷史資料或 MMIS 遠端資料。

## 驗證契約

- 單元測試：先加入兩筆「工單結案」加一筆「核簽中」的案例，確認修正前失敗、修正後通過。
- 整合驗證：執行指定 CLI，確認 `1151006-32` 的輸出值。
- 回歸測試：執行目標測試與完整 pytest。
- 型別檢查、Lint、Build、螢幕截圖：本次僅變更既有 Python 判斷和測試，不適用。
- 安全性檢查：確認沒有改動登入、網路或持久化邊界，且沒有存放 MMIS 回應。

## 完成證據

- 見 `../verification/depot-pending-approval-status.md`。
