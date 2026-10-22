# 驗證報告

## 摘要

- 任務：MMIS-060 待簽核且分析未完成時，Excel 備註填未處理。
- 結果：離線匯出與完整測試通過；未執行即時 MMIS 同步。
- 驗證者：Codex。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py::test_status_checks_write_matching_export_notes_only tests/test_unclosed_ab_xlsx.py::test_export_marks_pending_approval_without_analysis_as_unprocessed -q` | 修正前失敗 | 匯出測試顯示指定組合保留「原備註」；同步測試也顯示未完成分析會觸發資料充分性再查，故移除該不適用的測試。 |
| `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py::test_status_checks_write_matching_export_notes_only -q --tb=short` | 補充修正前失敗 | 加入 `(0,0,0,1,0,0)` 案例後，實際為「原備註」，預期「未處理」。 |
| `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py -q` | 通過 | 暫存 SQLite 匯出讀回 XLSX，檢查新組合、近似組合、既有規則與 SQLite SHA-256。 |
| `python -m pytest -q` | 通過 | 完整套件 exit code 0；既有 skip 不變。 |
| `python -m compileall -q tools/mmis_development/export_unclosed_ab_fault_notices_from_db.py tests/test_export_unclosed_ab_fault_notices_from_db.py` | 通過 | Python 語法檢查。 |
| `git diff --check` | 通過 | 無 whitespace error。 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 既有 `(NULL,1,0,1,0,0)` 對應「等候段修工單簽核中」，與新條件不同。 | 低 | 沿用查表邏輯，僅新增一筆。 |
| `1151017-30` 的即時查詢第一欄為 `NULL`，本機 SQLite 第一欄為 `0`，其餘五欄相同。 | 中 | 已確認同步流程會再次檢查資料充分性；補上 `(0,0,0,1,0,0)` 規則。 |

## 實際資料重現與修正

- 修正前以唯讀來源 `data/unclosed_ab_fault_notices.db` 匯出暫存 XLSX，找到 `1151017-30` 一筆，讀回備註為空白。
- SQLite 該筆六欄為 `(0,0,0,1,0,0)`，資料庫原備註為 `NULL`；即時查詢未加 `--check-analysis-readiness` 時第一欄為 `NULL`。
- 加入回歸案例後，修正前測試失敗，實際備註為「原備註」，預期「未處理」。
- 修正後使用相同來源資料庫匯出暫存 XLSX：`matching_rows=1`、`note_is_unprocessed=True`、`sqlite_unchanged=True`。

## 安全性與殘留風險

- SQLite 保持唯讀；Excel 字串仍強制使用文字型別，不執行公式。
- 即時 `--export-xlsx` 可能執行 MMIS 遠端故障分析寫入及付費 AI 流程，本次僅以隔離資料庫測試匯出路徑。
- UI 螢幕截圖不適用於 Python CLI；以 XLSX 讀回確認實際儲存格值。
