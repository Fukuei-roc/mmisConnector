# AI-Ready 任務卡

## Metadata

- 任務：查詢已派工日檢工單明細，條件符合時更新 SQLite 備註。
- 上層規格：`ai/artifacts/MMIS HTTP 未送簽核日檢工單查詢/feature-spec.md`。
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢。
- 上層 User Story：查詢並保留符合條件的日檢工單快照。
- 分軌：後端。
- 前置任務：現有 SQLite 快照與備註欄，已完成。
- 狀態：完成。
- 風險等級：高。明細讀取需 MMIS 網路與既有登入，SQLite 快照會重建。
- Agent owner：Codex。
- 人工核准者：使用者於本次對話直接指定行為並要求實作。

## 目標

每次建立 SQLite 快照後，為符合條件的已派工日檢工單填入「通知檢車室」。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py`、`tools/mmis_development/query_daily_inspection_work_order_details.py`、`src/mmis_connector/daily_inspection/reader.py`、`tests/test_query_daily_inspection_work_orders_not_submitted.py`。
- 既有模式：清單查詢後重建 SQLite；明細 Reader 回傳檢修記錄完成旗標與原始檢修人員清單；明細命令將人員分組。
- 假設：使用現有「備註欄」，不另建「備註」欄；依 SQLite 插入順序查詢；明細失敗時不寫入任何備註。
- 未知事項：Live MMIS 明細讀取時間與可用性。
- 允許變更的檔案：上述清單 wrapper、對應測試、本規格、任務卡與驗證紀錄。
- 不得觸碰：MMIS 認證、明細 Reader、其他功能模組、Excel 欄位契約。
- 驗證指令：對應 pytest、`compileall`、`git diff --check`、命令實際執行與 SQLite 查詢。
- 情境預算備註：讀專案地圖、查詢 wrapper、Reader 相關方法、測試及現有規格；跳過無關故障通報模組。

## 需求與驗收標準

- 快照建立後，只查詢「工作單狀態」等於「執行中已派工」的工作單。
- 重用清單查詢的 MMIS session，以既有明細 Reader 取得與明細命令等價的資料。
- 當 `maintenance_records_complete` 為 `True` 且兩組檢車室人員的 `records` 都是空清單時，僅該筆「備註欄」為「通知檢車室」。
- 其他狀態、未完成檢修記錄、任一組有人員時備註為空。
- 明細失敗或工作單號不符時，不提交部分備註。
- 現有 CLI 輸出與 Excel 欄位維持契約。

## 實作與驗證契約

- 以現有 Reader 與人員分組函式作為明細資料來源；SQLite 更新在全部明細讀取成功後以單一交易執行。
- 單元測試涵蓋符合、未完成、兩種人員非空、其他狀態、明細失敗與 session 重用。
- 無 UI，螢幕截圖不適用；不向 MMIS 寫入資料或輸出個資。

## 完成證據

- 見 `ai/artifacts/MMIS HTTP 未送簽核日檢工單查詢/verification/mark-vehicle-room-notice.md`。
