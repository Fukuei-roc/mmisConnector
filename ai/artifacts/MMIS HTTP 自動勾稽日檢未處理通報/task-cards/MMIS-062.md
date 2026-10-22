# AI-Ready 任務卡

## Metadata

- 任務：MMIS-062 將 `fault_notices` 改為可直接查看的 11 欄正體中文實體表。
- 上層規格：`../feature-spec.md` 的「實體表欄位修正」。
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報。
- 上層 User Story：直接開啟資料庫的 `fault_notices` 表即可查看指定欄位。
- 分軌：後端。
- 前置任務（dependsOn）：MMIS-061，已完成但未滿足實體表的使用情境。
- 狀態：完成。使用者於本次對話回報舊欄位仍可見，要求修正並驗證。
- 風險等級：高。既有 SQLite schema 與資料遷移。
- Agent owner：Codex。
- 人工核准者：本次對話使用者要求實作與驗證。

## 目標

`fault_notices` 實體表依指定順序只有 11 個正體中文欄位；既有批次狀態與資料可安全續跑。

## 情境包

- 相關檔案：`src/mmis_connector/auto_link/store.py`、`tests/test_auto_link_store.py`、`tests/test_auto_link_unprocessed_fault_notices.py`、`README.md`、既有 MMIS-061 規格與驗證紀錄。
- 既有模式：`fault_notices` 是含 27 欄的內部狀態表，`自動勾稽結果` 才是 11 欄檢視表；使用者重新執行後仍看到舊表。
- 假設：使用者查看的資料庫物件是 `fault_notices` 實體表。檢視表名稱保留為相容別名。
- 未知事項：無；目前檔案有 14 筆已完成資料，可用唯讀複本驗證遷移。
- 允許變更的檔案：上述程式、測試、README、本 Epic 的規格與驗證文件，以及受控備份後的本機 SQLite。
- 不得觸碰：MMIS 網路與遠端寫入流程、憑證、無關的 `.gitignore` 修改。
- 情境預算備註：已讀專案地圖、既有規格、store 與測試、目前 SQLite schema；未讀通報本文。

## 需求與契約

- 在單一 SQLite transaction 內將舊 `fault_notices` 轉成內部狀態表，建立 11 欄 `fault_notices`，完整回填既有列。
- 新資料庫直接建立同樣結構。狀態表與結果表須在同一交易中同步，崩潰或 rollback 不得留下不同步資料。
- `自動勾稽結果` 繼續提供相同 11 欄供既有查詢使用。
- `查詢時間` 為台北時間；`已關聯的工單` 僅在 `linked` 顯示；`關聯執行成功` 使用「是／否／未執行」。
- CLI 摘要、已完成批次更新、未完成批次續跑及禁止重送規則不變。

## 驗收標準

- `sqlite_master` 顯示 `fault_notices` 為 table；`PRAGMA table_info(fault_notices)` 精確等於指定 11 欄。
- 既有 14 筆資料的備份複本遷移後仍有 14 筆，原狀態與工單號保留；原檔未改動直到複本驗證通過。
- 新批次、逐筆狀態改變、中斷續跑及批次清除後，結果表與狀態表即時一致。
- 遷移失敗時整個交易 rollback；不對 MMIS 發送任何請求。

## 驗證契約

- 先以回歸測試重現原表欄位不符，再改實作並核對新表。
- 執行相關 pytest、全套 pytest、編譯與 `git diff --check`。
- 以現有資料庫的備份複本執行遷移與讀回；核對筆數、欄位、狀態及原始檔雜湊。
- 不執行會遠端寫入 MMIS 的正式批次。安全性與架構審查聚焦 migration 原子性、資料完整性與續跑。

## 完成證據

- 實作、遷移及驗證記錄於 `../verification/MMIS-062.md`。
