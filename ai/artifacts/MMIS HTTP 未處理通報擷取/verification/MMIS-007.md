# 驗證報告

## 摘要

- 任務：完整擷取未處理通報的所有分頁
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests\\test_parser.py tests\\test_query_unprocessed_fault_notices.py` | 通過 | 12 passed |
| `python -m pytest` | 通過 | 19 passed in 0.22s |
| `python -m compileall -q src tests` | 通過 | 無語法或 import 錯誤 |
| `python -m pip check` | 通過 | No broken requirements found |
| 離線解析錄製 HAR `req-00341` / `req-00343` | 通過 | `1-20/22` + `21-22/22`，合計 22 筆 |
| live `python -m mmis_connector query-unprocessed-fault-notices` | 通過 | exit 0、success true、21 筆、每筆 17 欄；輸出內容未記錄 |

## UI 證據

不適用；本次是 HTTP-only CLI 變更，沒有 UI 或視覺變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| Maximo 回應可能有其他 `.tCount`，不應盲目取第一個 | 中 | 已修正：限定為與「通報號」表頭相同的表格前綴 |
| 下一頁缺失、範圍不連續或總數改變可造成靜默漏資料 | 高 | 已修正：fail-closed 驗證並有回歸測試 |
| 錄製檔含敏感 session/資料 | 高 | 已管控：不複製入 repo，驗證只輸出範圍與筆數 |

## 審查結論

- 功能性：核准；單頁、空結果、20+2、三頁、缺頁、範圍不連續與總數改變皆有測試。
- 安全性：核准；未改變認證/授權，未新增依賴、外部 URL 或敏感資料記錄。
- 可維護性：核准；重用現有 parser 與 event 傳輸模式，公開 JSON schema 不變。
- 核准建議：核准。

## 殘留風險

- 分頁解析依賴 MMIS 現行 DOM 約定：`.tCount`、「通報號」表頭與 `tablebtn_next_on.gif`。DOM 改版時程式會回傳明確錯誤，而不是輸出不完整資料。
- 錄製證據僅有兩頁；三頁的 xhr sequence 行為由整合測試覆蓋，live 本次為兩頁 21 筆。

## Definition of Done

符合：實作、自動測試、語法/依賴檢查、錄製證據解析、live E2E、安全與可維護性審查皆有證據。
