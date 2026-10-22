# 驗證報告

## 摘要

- 任務：MMIS-063 將結果欄改名並區分查無日檢工單。
- 結果：通過。既有 SQLite 的 14 筆查無工單資料已完成本機遷移。
- 變更檔案：`src/mmis_connector/auto_link/store.py`、`tests/test_auto_link_store.py`、`README.md`、本 Epic 的功能規格、任務卡及本報告；另遷移預設 SQLite 資料庫。
- 審查：獨立代理檢查架構、資料遷移、交易回滾及測試，核准且無阻擋項目。

## 指令與結果

| 指令或檢查 | 結果 | 證據 |
|---|---|---|
| `$env:PYTHONPATH='src'; python -m pytest -q` | 通過，exit 0 | 全套測試到 100%；既有條件性測試略過。 |
| `python -m pytest tests/test_auto_link_store.py tests/test_auto_link_unprocessed_fault_notices.py -q` | 通過 | 獨立審查者執行，44 passed。 |
| `python -m compileall -q src tests` | 通過，exit 0 | 無編譯錯誤。 |
| `git diff --check` | 通過，exit 0 | 僅有既存 `.gitignore` 及功能規格的換行提示。 |
| 備份複本遷移 | 通過 | 原始 SQLite SHA-256 未變；複本末欄為「執行結果」，14 筆均為「未找到對應日檢工單」。 |
| 現有 SQLite 遷移後以全新唯讀連線查詢 | 通過 | `fault_notices` 實體表及 `自動勾稽結果` 檢視表均為指定 11 欄；14 筆結果均為新文字；內部 `no_matching_work_order` 仍為 14 筆。 |
| `PRAGMA integrity_check`、`PRAGMA foreign_key_check` | 通過 | 分別為 `ok` 與 0 個錯誤。 |

## 備份與回滾

- 遷移前用 SQLite backup API 建立 `data/auto_link_unprocessed_fault_notices.sqlite3.pre-mmis-063.bak`，保留舊欄名及 14 筆原始結果。
- 開啟資料庫時，在同一 SQLite 交易內改欄名、回填結果並重建同步觸發器；測試確認遷移失敗會保留舊 schema 與資料。必要時先停止使用資料庫的程序，再從備份還原。

## 安全性與殘留風險

- 僅改本機 SQLite，未連線或修改 MMIS 遠端資料，也未讀取或輸出通報明細與憑證。
- 其他既有狀態仍依原規則顯示「是／否／未執行」；例如 `query_failed` 仍顯示「未執行」。本任務只新增使用者指定的「未找到對應日檢工單」。
- 未試跑正式 MMIS 批次；後續正式執行後的遠端查詢與勾稽行為不在本次驗證範圍。

## UI 與後續任務

- 無 UI 變更，無螢幕截圖。後續任務無。
