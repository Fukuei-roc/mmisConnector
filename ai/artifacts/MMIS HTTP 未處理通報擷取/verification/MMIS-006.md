# 驗證報告

## 摘要

- 任務：將啟動指令改為可擴充的功能子命令
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest` | 通過 | 9 tests passed in 0.19s |
| `python -m compileall -q src tests` | 通過 | 無語法或 import 錯誤 |
| `python -m pip check` | 通過 | No broken requirements found |
| 無參數 `python -m mmis_connector` | 通過 | exit 1、錯誤 JSON 可解析、未登入 MMIS |
| live 新子命令 | 通過 | exit 0、JSON 可解析、16 筆、每筆 17 欄 |

## UI 證據

不適用；本次沒有 UI 變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 參數驗證必須早於 credentials 載入與登入 | 中 | 已由 dispatch 順序與單元測試確認 |
| 未知命令必須維持 JSON 錯誤契約 | 低 | 已測試 |

## 殘留風險

- 原本的無參數命令不再執行查詢；既有排程或 wrapper 必須補上 `query-unprocessed-fault-notices`。
- 未來子命令若需要參數，需在 command handler 層新增專屬參數解析與驗證。

## 審查結論

- 發現的問題：無未解決問題。
- 核准建議：核准。
