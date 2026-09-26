# 驗證報告：MMIS-015

## 摘要

- 任務：串接自動勾稽 CLI、公開 API 與整體驗證
- 結果：通過
- 驗證者：Codex
- Live MMIS：通過；2026-09-26 使用者受控執行 12 筆，全部為預期的無對應工單結果，未發生 mutation

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_cli.py tests/test_public_api.py -q` | 通過 | 16 passed；涵蓋命令 dispatch、登入前拒絕多餘參數、單一 client/store 串接、JSON 摘要與公開 API |
| `python -m pytest` | 通過 | 107 passed、3 skipped；skip 為既有選用錄製 DOM 缺檔 |
| `python -m compileall -q src tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | No broken requirements found |
| `git diff --check` | 通過 | 無 whitespace error；只有 Windows LF/CRLF 提示 |
| `python -m mmis_connector auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders` | 通過 | 修正車號規則後 run `d95faf6f5c1d49db8749df501d6f2c71` 完成；12 no-match、0 failed、0 manual review |

## UI 證據

- 不適用；本卡為 CLI、公開 Python API 與文件變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 多餘 CLI 參數若晚於設定載入才拒絕，可能發生不必要的憑證／網路邊界存取 | 中 | 已由測試確認在 `MMISConfig.from_env()` 前拒絕 |
| SQLite connection 若未關閉，可能留下檔案 handle | 中 | 已使用 `AutoLinkStore` context manager，測試確認離開流程時關閉 |
| 批次摘要可能洩漏逐筆內部資料 | 高 | 通過；CLI 只轉交 orchestrator 的計數與批次 metadata，不含來源 records |
| 寫入結果不明時若自動重送，可能重複勾稽 | 高 | 既有 MMIS-014 fail-closed 狀態機與回歸測試均通過；CLI 未新增 retry |

## 安全性與可維護性

- 沿用 `MMISConfig.from_env()`、單一 `MMISSession` 與既有 orchestrator，未新增認證或網路抽象。
- 固定本機 SQLite 路徑，不接受使用者路徑輸入，沒有新增 path traversal 或 command injection 面。
- 未新增 secret、cookie、token、原始 response 或逐筆通報的 stdout/log 輸出。
- 依賴未變更；`pip check` 通過。
- 公開 API 只新增 orchestrator 類別，既有命令與輸出契約保持不變。

## 殘留風險

- 本次 live 批次已驗證來源查詢、日檢查詢與摘要；因 12 筆皆無後續日檢工單，未觸發批次 mutation。
- SQLite 含內部故障通報資料，需由本機檔案權限保護。
- MMIS 與 SQLite 無分散式 transaction；`linking` 中斷會 fail closed 為需人工確認的 `link_error`，可能留下實際未送達但仍禁止自動重送的資料列。

## 核准建議

- 架構、安全性、測試與 code review：核准。
- Definition of Done：實作、離線驗證與人工 live 驗收均已滿足，可標記完成。
