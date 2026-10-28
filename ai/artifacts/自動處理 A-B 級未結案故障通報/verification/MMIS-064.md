# 驗證報告

## 摘要

- 任務：MMIS-064 含 ATP 故障分析未完成時填寫 Excel 備註。
- 結果：隔離 XLSX 匯出與完整測試通過；未執行即時 MMIS 同步。
- 驗證者：Codex。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py -q` | 8 項通過 | 修正前新案例顯示實際「原備註」；修正後讀回指定備註。 |
| `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py -q` | 通過，exit code 0 | 覆蓋匯出器與同步匯出路徑。 |
| `python -m pytest -q` | 通過，exit code 0 | 既有 skip 不變。 |
| `git diff --check` | 通過 | 無空白格式錯誤。 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 既有 `STATUS_RULES` 無 `(1,1,0,1,0,1)`，因此原備註未被覆蓋。 | 低 | 已新增精確對照並讀回 XLSX。 |
| 本機快照 9 筆沒有精確組合；`1151025-50` 本機六欄為 `(NULL,1,0,1,0,1)`。 | 低 | 以使用者提供的即時結果建立隔離測試；相近組合仍保留原備註。 |

## 殘留風險

- 未執行會連線 MMIS 並可能寫入遠端的即時同步命令。隔離資料庫與完整測試已驗證匯出行為。
- CLI/XLSX 無畫面截圖；驗證直接讀回儲存格並比對資料庫 SHA-256。
