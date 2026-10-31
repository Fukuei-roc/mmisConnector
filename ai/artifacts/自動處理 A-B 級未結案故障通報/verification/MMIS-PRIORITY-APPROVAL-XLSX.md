# 驗證報告

## 摘要

- 任務：`--export-xlsx` 新增優先簽核工單報表。
- 結果：通過離線完整測試及正式 MMIS 唯讀查詢；未執行會改寫 MMIS 的完整同步。
- 驗證者：Codex。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest -q` | 通過，exit code 0 | 完整套件；部分既有需外部條件的測試為 skip |
| `python -m compileall -q tools/mmis_development tests/test_priority_approval_xlsx.py` | 通過，exit code 0 | Python 編譯檢查 |
| `git diff --check` | 通過，exit code 0 | 差異格式檢查 |
| 既有 SQLite + `export_priority_xlsx(...)`，暫存輸出目錄 | 通過，exit code 0 | 11 個欄位項目去重為 9 張，MMIS 唯讀查詢後輸出 8 筆、1 欄的實際 XLSX |

## UI 證據

| Viewport | 螢幕截圖 | 備註 |
|---|---|---|
| 不適用 | 不適用 | CLI 與 Excel 檔案，無 UI 畫面變更 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 新增 Excel helper 需排除在 CLI 架構測試的工具數量之外 | 低 | 已修正，完整套件通過 |
| 不支援的工單類型需明確報錯，避免靜默漏報 | 中 | 已實作並納入規格 |

## 殘留風險

- 未執行正式完整同步指令，因原流程可能呼叫既有 MMIS 與 AI 寫入功能；雙報表流程以離線整合測試驗證。
- 輸出第一份報表成功而第二份查詢失敗時，JSON 會保留第一份路徑並回報第二份失敗；已完成的第一份報表不自動刪除。
