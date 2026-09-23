# 驗證報告

## 摘要

- 任務：實作 HTTP 登入與記憶體 Session
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest` | 通過 | 5 tests passed |
| `python -m compileall -q src tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | No broken requirements found |
| `git check-ignore -v .env` | 通過 | `.gitignore:1:.env` |
| live `python -m mmis_connector` | 通過 | 登入與同一 Session 後續請求成功 |

## UI 證據

不適用；本功能為 CLI，且需求禁止瀏覽器依賴。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| form action／redirect 需限制同源 | 中 | 已修正：所有 request 強制與 MMIS base URL 同源 |
| 未預期例外內容可能洩漏 | 中 | 已修正：stdout 只輸出遮罩後訊息 |
| POST 自動 retry 可能重播登入/event | 中 | 已修正：transport retry 僅允許 GET |

## 殘留風險

- MMIS 憑證鏈無法由目前 Python trust store 驗證；實際 `.env` 使用 `MMIS_VERIFY_SSL=false`。應取得機關 CA bundle 後改回 `true`。
- 權限由 MMIS 伺服器控制；本工具不另行實作授權層。
