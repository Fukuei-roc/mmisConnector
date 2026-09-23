# 驗證報告

## 摘要

- 任務：實作未處理通報查詢與 JSON CLI
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest` | 通過 | 5 tests passed in 0.23s |
| 錄製 DOM 解析測試 | 通過 | 16 筆、每筆 17 欄 |
| live `python -m mmis_connector` | 通過 | exit 0、JSON 可解析、16 筆、每筆 17 欄 |
| 缺少 credentials 的 CLI 測試 | 通過 | exit 1，仍輸出可解析安全 JSON |
| browser dependency scan | 通過 | `src/`、`tests/`、依賴與 README 無 Playwright/Selenium |
| PowerShell governance equivalent check | 通過 | 必要檔案與 skill stubs 皆存在 |

## UI 證據

不適用；本功能為 CLI。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| Maximo XML CDATA 內的 HTML 未被 parser 視為元素 | 高 | 已修正並以 live query 驗證 |
| 顏色查詢表頭夾帶圖例造成錯誤 JSON key | 中 | 已正規化並加入錄製 DOM regression test |

## 殘留風險

- Maximo 若變更表格 ID 規律、app id 或儲存查詢名稱，需更新 parser/event constants。
- 錄製 DOM regression test 預設引用使用者提供的本機 evidence 路徑；搬移專案時需同步提供該 evidence 或調整測試 fixture。
- `scripts/check-governance.sh` 因本機沒有可用 WSL distribution 而無法執行；已以等價 PowerShell 檢查覆蓋必要檔案與 skill stubs。
