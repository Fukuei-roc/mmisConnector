# 驗證報告：刪除五個重複查詢入口

## 摘要

- 結果：通過。
- 驗證者：Codex。
- 變更：刪除五個單項查詢入口，確認開發工具 README 不再列出這些指令，並讓架構測試核對 17 個保留入口。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -B -m pytest tests/test_architecture.py tests/test_development_tools.py tests/test_fault_notice_full_detail.py tests/test_daily_inspection_inspection_records.py -q -o addopts='' -p no:cacheprovider` | 51 passed，7 skipped | 架構、保留入口、完整通報與日檢明細 |
| `python -B -m pytest -q -o addopts='' -p no:cacheprovider` | 604 passed，48 skipped | 完整離線測試 |
| `Test-Path` 檢查五個入口 | 五個皆為 `False` | 沒有刪除其他工具 |
| `Get-ChildItem tools/mmis_development -Filter '*.py'` 並排除四個共用檔案 | 17 個可執行工具 | 與 README、架構測試一致 |
| `rg` 以完整模組名稱搜尋 `src`、`tests`、`tools/mmis_development`、現行 README、`docs/development`、`ai/context` | 精確引用 0 筆 | 歷史規格與看板卡片保留原紀錄 |
| `git diff --check` | 通過 | 無 whitespace 錯誤 |

Pytest 執行時設定 `PYTHONDONTWRITEBYTECODE=1`。本次不連線 MMIS，也不執行有寫入副作用的開發工具。

## 審查發現

- `src/mmis_connector/` 的登入、查詢、解析與寫入程式未修改。
- 開發工具 README 已移除五個舊入口的指令，列出 17 個保留工具。
- 完整通報與日檢明細功能仍由既有測試覆蓋。
- UI 證據不適用。

## 殘留風險

- 48 個跳過的測試未在本次執行。
- Repo 之外的排程、捷徑或人工腳本是否呼叫舊指令，無法由 repo 內測試確認。
