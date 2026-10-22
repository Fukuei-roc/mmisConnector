# 驗證報告

## 摘要

- 任務：MMIS-062 將 `fault_notices` 改為 11 欄正體中文實體表。
- 結果：通過。現有 14 筆 SQLite 資料已完成本機遷移，未執行 MMIS 遠端批次。
- 驗證者：Codex；另由獨立審查代理檢查架構、安全性及測試。
- 變更檔案：`src/mmis_connector/auto_link/store.py`、`tests/test_auto_link_store.py`、`tests/test_auto_link_unprocessed_fault_notices.py`、`README.md`、本 Epic 的規格、任務及驗證文件。

## 指令與結果

| 指令或檢查 | 結果 | 證據 |
|---|---|---|
| 修正前檢查 `PRAGMA table_info(fault_notices)` | 重現問題 | 首欄實際為 `id`，預期為「查詢時間」，另有 16 個舊欄位。 |
| `$env:PYTHONPATH='src'; python -m pytest -q` | 通過，exit 0 | 全套測試到 100%；36 項依既有條件略過。 |
| `python -m pytest tests/test_auto_link_store.py tests/test_auto_link_unprocessed_fault_notices.py -q` | 通過，41 passed | 獨立審查者執行；涵蓋遷移、續跑、同步與回滾。 |
| `python -m compileall -q src tests` | 通過，exit 0 | 無編譯錯誤。 |
| `git diff --check` | 通過，exit 0 | 有既存 `.gitignore` 與文件換行提示。 |
| 備份複本遷移 | 通過 | 11 欄實體表、14 筆結果及 14 筆內部狀態，原狀態計數不變；來源檔 SHA-256 未變。 |
| 現有 SQLite 本機遷移與全新唯讀連線查詢 | 通過 | `fault_notices` 為 table，精確 11 欄、14 筆；目前 14 筆「關聯執行成功」皆為「未執行」。 |
| `PRAGMA integrity_check` 與 `PRAGMA foreign_key_check` | 通過 | 分別為 `ok` 與 0 個錯誤。 |

## 備份與回滾

- 遷移前使用 SQLite backup API 建立 `data/auto_link_unprocessed_fault_notices.sqlite3.pre-mmis-062.bak`，內含遷移前 14 筆資料。未覆寫此備份。
- 遷移在單一 SQLite transaction 內執行；測試確認失敗會保留舊表。若需要人工回滾，應停止所有使用此資料庫的程序，再由備份還原；舊程式與新 schema 不相容。

## 審查發現

- 初次審查發現每次開啟會重寫結果表，以及缺少失敗同步的回滾測試。兩項均已修正並新增對應測試。
- 最終獨立審查核准，未發現阻擋問題。

## 殘留風險

- `fault_notices` 是供查閱的實體結果表。外部程式若直接修改它，可能與 `auto_link_state` 內部狀態不一致；README 已標明請勿手動修改。
- 「查詢時間」取自來源查詢後匯入資料的時間，非 MMIS 伺服器回傳時間。
- 未執行正式 MMIS 批次，因它可能寫入遠端資料；本次驗證只涵蓋本機 SQLite 遷移與模擬流程。

## UI 證據與後續任務

- 無 UI，無螢幕截圖。後續任務無。
