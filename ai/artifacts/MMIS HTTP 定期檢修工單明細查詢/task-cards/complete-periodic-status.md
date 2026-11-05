# AI-Ready 任務卡

## Metadata

- 任務：查詢完整定期檢修工單狀態。
- 上層規格：`../feature-spec-complete-status.md`。
- 上層 Epic：MMIS HTTP 定期檢修工單明細查詢。
- 上層 User Story：查詢主工單的全部子工單狀態。
- 分軌：後端。前置任務：無。
- 狀態：待人工驗收。風險等級：中。
- Agent owner：Codex。
- 人工核准：使用者於 2026-11-05 指定程式、輸入、輸出、錄製案例與單筆查詢範圍。

## 情境包

- 相關檔案：`src/mmis_connector/periodic_inspection/query.py`、`reader.py`、`status.py`、`events.py`、`parser.py`、`tools/mmis_development/query_complete_periodic_inspection_work_order_status.py`、指定錄製目錄。
- 既有模式：`MMISSession` 登入，`MaximoEventClient` 切換 app 與送出事件，以動態表頭和分頁計數解析表格，development tool 印 JSON。
- 假設：工作單主號對應帶數字尾碼的子工單；`母工單=0` 是錄製查詢條件。
- 未知事項：錄製目錄缺 `raw.har`；第二筆的 DOM snapshot 停在第一筆結果，須用即時查詢核對。
- 允許變更的檔案：新 status 模組、新 development tool、新測試、`tests/test_architecture.py` 的模組清單與工具數量、本 Epic 的規格、任務卡與驗證報告。
- 不得觸碰：登入、共用 event transport、既有工單查詢語義、錄製原檔、憑證。
- 情境預算：讀專案地圖、流程、相鄰查詢、parser、錄製摘要、時間線及畫面；未讀其他 MMIS domain。

## 驗收與驗證契約

- 一次只接受一筆工作單並印一次 JSON。
- 兩筆錄製案例的筆數分別為 3 與 2；五欄均存在；TR 級別不得被排除。
- 查詢使用「所有記錄」、工作單、母工單與 filterrows；讀完所有分頁。
- 結果不符、重複、缺欄、分頁不完整時輸出 JSON 錯誤。
- 跑目標測試、相關回歸測試、全套測試、編譯與即時唯讀查詢。
- 架構測試原有清單落後現有三個模組；本任務新增模組後一併更新清單與工具數量，不更動其依賴檢查邏輯。
- 無 UI、資料遷移或遠端寫入。安全審查確認不印出密鑰與 session。

## 完成證據

- 見 `../verification/complete-periodic-status.md`。
