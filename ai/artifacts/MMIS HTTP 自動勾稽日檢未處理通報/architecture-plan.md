# 架構計畫

## Metadata

- Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層規格：`ai/artifacts/MMIS HTTP 自動勾稽日檢未處理通報/feature-spec.md`
- 狀態：待人工核准
- 風險：高

## 架構摘要

功能維持既有分層：CLI 只處理參數、設定與 JSON 輸出；新 orchestrator 編排三個既有領域物件；新 SQLite store 單獨負責 schema、transaction、狀態轉移與續跑判斷。三個既有 MMIS 功能共享同一個 `MMISSession`，不以 subprocess 串接，也不新增瀏覽器或 ORM。

```text
cli.py
  -> AutoLinkUnprocessedFaultNotices(client, store)
       -> UnprocessedFaultNoticeQuery(client)
       -> DailyInspectionWorkOrderQuery(client)
       -> DailyInspectionWorkOrderFaultNoticeLinker(client)
       -> AutoLinkStore(sqlite3)
```

## 預計變更檔案

- 新增 `src/mmis_connector/auto_link_store.py`：SQLite schema、批次生命週期、逐列狀態與摘要。
- 新增 `src/mmis_connector/auto_link_unprocessed_fault_notices_to_daily_inspection_work_orders.py`：來源驗證、工單選擇與批次編排。
- 修改 `src/mmis_connector/cli.py`：註冊無參數批次命令，共用單一 client。
- 修改 `src/mmis_connector/__init__.py`：公開新 orchestrator。
- 修改 `.gitignore`：忽略預設 runtime SQLite 路徑或 `*.sqlite3` 的明確專案資料目錄。
- 修改 `README.md`：命令、資料庫路徑、續跑與不可重試語意。
- 新增 `tests/test_auto_link_store.py`。
- 新增 `tests/test_auto_link_unprocessed_fault_notices.py`。
- 修改 `tests/test_cli.py`、`tests/test_public_api.py`。
- 新增本 Epic 的驗證報告；必要時最小更新專案地圖／搜尋指南。

## CLI 契約

```text
python -m mmis_connector auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders
```

- 不接受位置參數。
- 預設資料庫：`data/auto_link_unprocessed_fault_notices.sqlite3`。
- stdout 僅輸出 JSON 摘要。
- 成功完成批次時 exit code 0；初始化、來源擷取或資料庫層級失敗時 exit code 1。
- 單筆業務失敗不終止整批；摘要以計數呈現。

成功摘要契約：

```json
{
  "success": true,
  "operation_name": "自動勾稽日檢未處理通報",
  "run_id": "...",
  "resumed": false,
  "total": 0,
  "linked": 0,
  "no_matching_work_order": 0,
  "ambiguous_work_order": 0,
  "invalid_source_data": 0,
  "query_failed": 0,
  "link_error": 0,
  "manual_review_required": 0,
  "database_path": "data/auto_link_unprocessed_fault_notices.sqlite3"
}
```

## SQLite 契約

### `runs`

- `run_id TEXT PRIMARY KEY`
- `status TEXT NOT NULL CHECK(status IN ('running', 'completed'))`
- `source_query_name TEXT`
- `started_at TEXT NOT NULL`
- `completed_at TEXT`

### `fault_notices`

- `id INTEGER PRIMARY KEY`
- `run_id TEXT NOT NULL REFERENCES runs(run_id)`
- 17 個來源欄位採 snake_case 英文欄名，值保存為 TEXT；另存 `source_record_json TEXT NOT NULL` 以無損保留來源。
- 核心欄位：`fault_notice_no`（來源「通報號」）、`vehicle`（來源「車組/車號」）、`occurrence_date`（來源「發生日期」）。
- 結果欄位：`daily_inspection_work_order_no TEXT`（顯示語意「日檢工單號」）、`processing_status TEXT NOT NULL`、`result_message TEXT`、`attempt_count INTEGER NOT NULL DEFAULT 0`、`created_at TEXT NOT NULL`、`updated_at TEXT NOT NULL`。
- `UNIQUE(run_id, fault_notice_no)`。
- 狀態集合：`pending`、`query_failed`、`invalid_source_data`、`no_matching_work_order`、`ambiguous_work_order`、`work_order_selected`、`linking`、`linked`、`link_error`。

## 狀態與恢復契約

- 沒有 `running` 批次：以單一 transaction 刪除舊 `fault_notices`／`runs`，建立新 run，再擷取及匯入來源資料。
- 有 `running` 批次：不重新擷取來源資料，直接續跑。
- 可處理狀態：`pending`、`query_failed`。
- 終止且不可自動重做：`invalid_source_data`、`no_matching_work_order`、`ambiguous_work_order`、`linked`、`link_error`。
- `work_order_selected` 可在尚未送出勾稽前繼續；送出前先持久化為 `linking`。
- 啟動時若發現 `linking`，因無法證明前次寫入是否已送達，轉為 `link_error` 並記錄「前次勾稽結果不明，需人工確認」，不得重送。
- 任一 linker 例外都轉成 `link_error`；錯誤訊息需去敏，不可保存 response body、token 或 session 資訊。
- 含 `link_error` 的 run 不標記完成，因此重新啟動只會保留並跳過錯誤列，不會清除資料後建立可能重送相同通報的新 run。
- orchestrator 執行期間持有獨立 SQLite lock database 的 `BEGIN IMMEDIATE` 鎖；主資料庫仍可逐列 commit。第二個程序無法取得鎖時在 MMIS 操作前失敗，程序崩潰時鎖由 OS／SQLite 自動釋放。
- 每次狀態轉移獨立 commit；SQLite 啟用 foreign keys，採預設 rollback journal 或 WAL 由實作測試決定，不承諾跨網路與 DB 的分散式原子性。

## 工單決策契約

1. 驗證每筆查詢結果具有合法 `工作單` 及 `檢修日期`。
2. 僅保留檢修日期嚴格晚於來源發生日期的資料；既有 MMIS `>` 查詢之外再做本機防禦性檢查。
3. 依檢修日期升冪找出最早日期。
4. 該日期只有一個不同工作單號時選用它；重複的相同工作單列去重。
5. 同一最早日期有多個不同工作單時標記 `ambiguous_work_order`，不得勾稽。

## 安全性與隱私

- 使用參數化 SQL；不由來源欄位動態拼 SQL identifier。
- runtime DB 不進 Git；路徑限制於專案 `data/`，父目錄按需建立。
- runtime DB 與 execution-lock DB 均不進 Git。
- 不儲存 MMIS 憑證、cookie、token、session id 或原始 HTML。
- 重用既有 linker 的精確工作單驗證與成功後領域驗證。
- `linking` 必須先 commit，再呼叫遠端寫入，以 crash window 保守換取不重複寫入。
- 勾稽 transport 禁止自動 retry；任何勾稽錯誤永久停止該列並要求人工檢查。

## 遷移與回滾

- 這是新資料庫，無既有 schema migration。
- 若 schema 版本不相容，明確失敗，不自行破壞未知資料；本功能的下一版再引入 schema version migration。
- 程式碼回滾只需移除新 CLI 與新模組；SQLite 是 runtime artifact，可由人工備份或刪除，不納入 Git 回滾。

## 測試策略

- Store 單元測試使用 pytest `tmp_path`，驗證 schema、清除、續跑、唯一鍵、每列 commit 與 `linking` 恢復。
- Orchestrator 以 fake query／linker 驗證 session 物件共享、來源轉換、日期條件、工單決策、逐列容錯與不可重試狀態。
- CLI 測試 monkeypatch 設定與依賴，不連線 MMIS。
- 全套回歸、compileall、pip check、diff check。
- 不在未取得額外一次性授權前執行 live 批次勾稽。

## 任務順序

1. `MMIS-013`：建立 SQLite 可恢復狀態層。
2. `MMIS-014`：建立批次查詢、選單與勾稽編排器（依賴 `MMIS-013`）。
3. `MMIS-015`：串接 CLI、公開 API、文件與整體驗證（依賴 `MMIS-014`）。

## Review Gates

- 產品：已核准功能規格與補充錯誤政策。
- UI：不適用。
- 架構：高風險，實作前需人工核准本計畫。
- 安全性：實作後審查 SQLite 敏感資料、SQL 注入、遠端 mutation crash window 與 log 去敏。
- 測試：實作後審查狀態機、中斷恢復及不重複勾稽證據。
- Code review：實作後檢查範圍、既有契約與架構偏移。
