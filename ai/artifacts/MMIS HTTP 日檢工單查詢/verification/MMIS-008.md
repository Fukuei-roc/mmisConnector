# 驗證報告

## 摘要

- 任務：實作 HTTP-only 日檢工單查詢 CLI
- 結果：通過，待人工驗收
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest` | 通過 | 33 passed、1 skipped；跳過項目依賴本機已不存在的舊故障通報錄製 DOM，新日檢錄製 DOM 測試已通過 |
| `python -m compileall -q src tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | No broken requirements found |
| `git diff --check` | 通過 | 僅有 Windows LF/CRLF 提示，無 whitespace error |
| JSON parse：`epics.json`、`MMIS-008.json` | 通過 | 治理資料格式有效 |
| Browser dependency scan | 通過 | `src`、`tests` 無 Playwright／Selenium 參照 |
| `python -m mmis_connector query-daily-inspection-work-orders 703 2026/09/22` | 通過 | HTTP-only live 查詢回傳 1 筆，工作單為錄製對應的 `115-1A-*` 結果 |
| `python -m mmis_connector query-daily-inspection-work-orders 999999 2099/12/31` | 通過 | exit code 0、count 0、records 空陣列、message 為「找不到對應工單」 |
| `python -m mmis_connector query-unprocessed-fault-notices` | 通過 | 共用 event refactor 後的既有功能 live 回歸成功，回傳 19 筆 |
| `python -m mmis_connector query-daily-inspection-work-orders 703 2026/02/30` | 通過 | exit code 1，安全回報日期格式錯誤，未進入 MMIS 查詢流程 |

## UI 證據

不適用；本任務沒有 UI 或瀏覽器依賴。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 清理舊查詢 import 時曾誤刪仍需使用的 `html`，live 回歸出現 NameError | 高 | 已修正，完整測試與舊功能 live 回歸皆通過 |
| 既有故障通報測試依賴一份本機已不存在的外部錄製 DOM | 低 | 測試改為缺檔時明確 skip，不隱藏其他測試失敗 |
| 錄製目錄沒有 README 所述的 `raw.har` | 中 | 以 timeline、成功 DOM、既有知識與 live 查詢交叉驗證；列為殘留風險 |

## 安全性與可維護性審查

- 功能性：成功、空結果、無效輸入、單頁完整性與舊功能回歸均有證據。
- 身分驗證：沿用 `.env` 與程序內 `requests.Session`，沒有新增憑證儲存。
- 網路邊界：沿用 `MMISSession.request` 的 HTTPS 同源檢查、timeout 與安全錯誤封裝。
- 輸入：車號 trim 且不得空白；日期驗證為真實日曆日期；event value 經 JSON 編碼。
- 隱私：未將錄製 cookie、token、session id、帳密或完整 response 寫入 repo。
- 維護性：抽出 `MaximoEventClient` 供新舊功能重用；動態 table prefix 由欄名集合解析，未寫死錄製 ID。
- 核准建議：核准。

## 殘留風險

- 日檢工單結果若超過單頁會明確失敗，避免回傳不完整資料；未實作日檢分頁。
- MMIS 若改變欄名、C1/C3/C11 語義或 event 協定，需要更新解析與事件映射。
- 錄製證據缺少 raw HAR，但 live 成功與空結果已驗證目前實際協定。
- 共用知識庫已新增 `stableWorkflows.daily-inspection-work-order-http-query`，沒有取代或 deprecated 舊指引。
