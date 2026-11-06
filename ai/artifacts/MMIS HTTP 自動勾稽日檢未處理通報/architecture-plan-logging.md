# 自動勾稽執行紀錄架構

## 情境包

- 任務：為正式 auto-link CLI 增加可供事後排障的執行紀錄。
- 相關檔案：`src/mmis_connector/cli.py`、`src/mmis_connector/auto_link/orchestrator.py`、`src/mmis_connector/auto_link/store.py`、`src/mmis_connector/daily_inspection/query.py`、`tests/test_cli.py`、`tests/test_auto_link_unprocessed_fault_notices.py`。
- 既有模式：CLI 保持 stdout JSON；orchestrator 逐列編排查詢與勾稽；SQLite 只保存最終狀態，沒有查詢快照；`/logs/` 原已列入 `.gitignore`。
- 路徑：以 source module 的位置定位專案根目錄，避免工作目錄不同時把 log 寫到其他地方；既有 `data/` 路徑規則不變。
- 未知事項：MMIS 不提供這個流程可供回讀的歷史查詢回應，因此零筆紀錄不能證明工單當時的狀態。
- 允許變更：上述 CLI、auto-link 模組與測試、`.gitignore`、`logs/README.md`、本 Epic 的規格與驗證文件。
- 不得觸碰：MMIS 認證、HTTP 事件、勾稽規則、SQLite schema、其他命令的行為。
- 驗證指令：`python -m pytest tests/test_cli.py tests/test_auto_link_unprocessed_fault_notices.py -q`、`python -m pytest -q`、`git diff --check`。
- 風險：中。紀錄檔含內部通報與工單識別碼，須避免寫入密鑰或完整通報資料。
- 情境預算：讀取 project map、architecture map、code-search guide、CLI、orchestrator、store、日檢查詢及對應測試；略過無關的 UI 與其他 domain。

## 設計決策

CLI 建立專屬 logger 與檔案處理器，orchestrator 只發送允許欄位的 JSON Lines 事件。每次執行使用獨立檔案，完成或失敗時關閉處理器。檔案寫入失敗時在 stderr 發出一次安全化警告，不改變 MMIS 勾稽結果。這維持現有查詢與勾稽的資料契約，且不讓 log 寫入 MMIS 的原始回應。

另一方案是將自訂 journal 物件注入每個 domain 元件。該方案需擴大 constructor 與依賴面；目前只有 auto-link 需要紀錄，所以先用 Python 標準 `logging`。其他命令將來可沿用相同路徑與檔案規則，不必共用 auto-link 的事件欄位。

## 安全與驗證

只允許通報號、車號、日期、工單號、狀態、筆數、批次識別碼與安全化錯誤訊息。禁止保存帳密、cookie、token、故障現象、完整來源資料與完整 HTML。執行檔案由 Git 忽略，不設自動清理。測試直接讀取產生的 JSONL，核對事件順序、條件、結果與敏感值排除。
