# 驗證報告

## 摘要

- 任務：MMIS-061 提供自動勾稽結果的正體中文 SQLite 檢視表。
- 結果：通過。
- 驗證者：Codex；另有獨立唯讀安全與正確性審查。
- 變更檔案：`src/mmis_connector/auto_link/store.py`、`tests/test_auto_link_store.py`、`README.md`、本 Epic 的規格、任務卡與本報告。
- 行為：新增 `自動勾稽結果` 檢視表。現有兩張資料表、CLI 輸出與 MMIS 遠端勾稽流程維持原契約。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `$env:PYTHONPATH='src'; python -m pytest -q` | 通過，exit 0，進度 100% | 全套測試；少數既有測試依條件略過。 |
| `python -m pytest -q -p no:cacheprovider tests/test_auto_link_store.py tests/test_auto_link_unprocessed_fault_notices.py` | 通過，35 passed | 獨立審查者執行。 |
| `python -m compileall -q src tests` | 通過，exit 0 | 無編譯錯誤。 |
| `git diff --check` | 通過，exit 0 | 僅有既存 `.gitignore` 與文件的換行提示。 |
| 唯讀開啟現有 SQLite，備份到暫存庫後建立新檢視表並查詢 | 通過 | 精確 11 欄；既有 13 筆全可讀，13 筆查詢時間均含 `+08:00`。原始 SQLite SHA-256 前後相同。暫存複本已刪除。 |

## UI 證據

無 UI，螢幕截圖不適用。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 獨立審查未發現阻擋問題。 | 無 | 核准。 |
| 新測試以移除新建庫的檢視表模擬舊庫。 | 低 | 已另以現有 SQLite 的唯讀複本驗證舊庫相容。 |

## 殘留風險

- `查詢時間` 取自來源查詢完成後開始匯入的時間，並非 MMIS 伺服器回傳的精確時間。
- 若既有資料異常地把缺少工單號的列標成 `linked`，檢視表會顯示「是」但工單欄為空；現行編排器的正常成功路徑會儲存工單號。
- 未執行會對 MMIS 寫入的正式批次。此次只變更 SQLite 檢視表，未改寫遠端操作。

## 後續任務

- MMIS-062：使用者重新執行後仍在 `fault_notices` 實體表看到舊欄位。MMIS-061 只新增檢視表，未滿足直接開啟實體表的需求；以 MMIS-062 修正。
