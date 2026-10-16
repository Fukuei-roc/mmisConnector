# 驗證報告

## 摘要

- 任務：ATP 故障分析選項 HTTP 遍歷與 JSON 匯出
- 結果：通過
- 驗證者：Codex，2026-10-16

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_atp_options.py -q` | 通過 | 解析、分頁、合法空清單、階層、partial、唯讀 allowlist、CLI 狀態 |
| `python -m pytest -o addopts='' --disable-warnings` | 通過 | 全專案 295 passed、39 skipped；skip 為既有錄製證據缺失 |
| `python -m py_compile src/mmis_connector/fault_notices/atp_options.py tools/mmis_development/export_atp_fault_analysis_options.py tests/test_atp_options.py` | 通過 | 語法檢查 |
| `python -m tools.mmis_development.export_atp_fault_analysis_options 1151012-36` | 通過 | HTTP session，`completed`，6/23/65/65 |
| `git diff --check` | 通過 | 無 whitespace error；有既有 CRLF 轉換提醒 |
| `python -m ruff check ...` | 未執行 | 本環境未安裝 ruff |

## UI 證據

無 UI 變更，螢幕截圖不適用。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| Maximo 零筆 lookup 仍有表頭但可含「沒有要顯示的列」 | 中 | 已補解析與測試 |
| 錄製僅示範一條路徑 | 中 | 以 live HTTP 完整遍歷並比對統計 |
| MMIS lookup 使用 POST event | 高 | 僅允許 click 查詢、選取、分頁、取消及頁籤；未送儲存事件 |

## 殘留風險

- MMIS 日後若變更 lookup DOM 或自動儲存語義，工具會因解析或選取驗證失敗而輸出 partial；需重新錄製確認。
- 本次 live 資料六個要因均有因子，23 個因子均有項目；合法空分支由離線測試驗證。
- Session 過期或中斷會保留錯誤分支的 partial 檔，需重新執行取得完整成果。
