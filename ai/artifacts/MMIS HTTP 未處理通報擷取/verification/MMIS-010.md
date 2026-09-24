# 驗證報告

## 摘要

- 任務：比較兩種未處理通報並擷取較多者
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_query_unprocessed_fault_notices.py -q` | 通過 | 10 passed；覆蓋兩種大小關係、平手、零筆、雙查詢事件順序、多頁及失敗路徑 |
| `python -m pytest` | 通過 | 56 passed, 3 skipped |
| `python -m compileall -q src tests` | 通過 | 無輸出，exit 0 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 無 whitespace error；僅 Git CRLF 提示 |
| README 內容對照 | 通過 | 已說明雙查詢順序、較大筆數選擇、平手規則、選定結果分頁與 `query_name` 語義 |
| `python -m mmis_connector query-unprocessed-fault-notices`（僅輸出非敏感摘要） | 通過 | `success=true`、選定車輛配屬段、`count=14`、`record_count=14` |

## UI 證據

不適用：本任務是 HTTP-only CLI 邏輯，沒有 UI 變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 無功能性、安全性、隱私、架構偏移或維護性阻擋問題 | 無 | 核准建議：核准 |

## 審查備註

- 功能：依錄製順序先車輛配屬段、後開單時所屬段；平手或第一個較多時會重新切回第一個查詢。
- 分頁：只擷取選定查詢的後續頁，且保留總筆數、範圍連續、next target 與最終筆數驗證。
- 安全：沒有新增外部輸入、URL、憑證、日誌或依賴；live 驗證未將 records 寫入報告。
- 可維護性：保留 `QUERY_NAME` 與現有 public class/CLI，將 saved-query 選擇與分頁收集分開，沒有新增抽象層或瀏覽器 fallback。

## 殘留風險

- 2026-09-24 錄製目錄沒有 `raw.har`，關鍵 query event 以 `timeline.json` 與最終 DOM 交叉驗證。
- live 當下兩個查詢均為 14 筆，實際環境只走過平手分支；開單時所屬段較多與多頁分支由單元／整合式 fake response 測試驗證。
- 仍依賴 MMIS 現有 saved-query 名稱、`.tCount`、表頭與 next-page DOM 約定；結構改變時會 fail closed。
