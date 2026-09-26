# 驗證報告：MMIS-016

## 摘要

- 任務：修正自動勾稽的來源車號正規化
- 結果：通過
- 驗證者：Codex
- Live MMIS：通過；使用者於 2026-09-26 受控執行，結果符合「12 筆皆無後續日檢工單」的預期，未發生 mutation

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_auto_link_unprocessed_fault_notices.py -q`（實作前） | 預期失敗 | ImportError：正規化函式尚不存在，證明新增測試可攔截缺陷 |
| `python -m pytest tests/test_auto_link_unprocessed_fault_notices.py -q` | 通過 | 21 passed；涵蓋代表車號、無數字拒絕、query 參數與 SQLite 原值保存 |
| `python -m pytest` | 通過 | 119 passed、3 skipped；skip 為既有選用錄製 DOM 缺檔 |
| `python -m compileall -q src tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | No broken requirements found |
| `git diff --check` | 通過 | 無 whitespace error；只有 Windows LF/CRLF 提示 |
| `python -m mmis_connector auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders` | 通過 | run `d95faf6f5c1d49db8749df501d6f2c71`；12 筆完成、12 筆無對應工單、0 linked、0 failed、0 manual review |

## UI 證據

- 不適用；本卡沒有 UI 變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 來源單車碼原樣送入 C3，造成 `EP9393` 等值查不到日檢工單 | 高 | 已修正：查詢前正規化為 `939` |
| 若修改通用 query normalizer，可能破壞既有 CLI 公開契約 | 中 | 已避免：新增 orchestrator 專用 pure function |
| 正規化後若覆寫 SQLite 原值，會降低稽核性 | 中 | 已避免並有整合測試：SQLite 保留 `EP9393`，fake query 收到 `939` |
| 無數字來源若送入 MMIS，會產生無效查詢 | 中 | 已修正：標記 `invalid_source_data` 前即拒絕 |

## 安全性與可維護性

- 未新增 MMIS request、retry、權限或憑證處理。
- 正規化函式無 I/O，使用固定 ASCII 數字規則，沒有注入或路徑風險。
- 通用 `normalize_vehicle()` 與既有 CLI 契約保持不變。
- 寫入前的 `linking` commit、結果驗證與 fail-closed 行為未變。
- SQLite schema 與 runtime DB 均未修改。

## 殘留風險

- 「首位 9 的四位數即 900 型單車碼」依使用者提供的業務規則實作；新車型或其他四位編碼需另行擴充。
- 本次 live 資料沒有可勾稽工單，因此尚未以批次流程產生實際 mutation；單筆 linker 的 live 寫入驗證另已於既有任務完成。

## 核准建議

- 架構、安全性、測試與 code review：核准。
- Definition of Done：實作、離線驗證與人工 live 驗收均已滿足，可標記完成。
