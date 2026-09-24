# 驗證報告

## 摘要

- 任務：MMIS-012 實作 HTTP-only 日檢工單故障通報勾稽 CLI
- 結果：通過（2026-09-24 人工驗收完成）
- 驗證者：Codex
- 驗證日期：2026-09-24

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_link_fault_notice_to_daily_inspection_work_order.py tests/test_events.py tests/test_read_daily_inspection_work_order.py tests/test_cli.py tests/test_public_api.py` | 通過 | `49 passed, 1 skipped`；涵蓋新功能與直接回歸範圍 |
| `python -m pytest -rs` | 通過 | `85 passed, 3 skipped in 0.52s` |
| `python -m compileall -q src tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 無 whitespace error；僅 Windows CRLF 提示 |
| 錄製 XHR／DOM 唯讀檢查 | 通過 | 寫入回應含 `1150923-36` 與「故障通報管理」；返回回應含日檢工單必要表頭 |
| `query-daily-inspection-work-order-by-number 115-1A-71002` | 通過 | live 前置唯讀查詢成功，唯一工單可解析，共 6 筆 |
| `query-daily-inspection-work-order-by-number-and-link-fault-notice 115-1A-71002 1150923-36` | 通過 | 只執行一次；exit code 0、`linked=true`、`returned_to_list=true` |
| live 後置唯讀查詢 | 通過 | 指定故障通報存在，總筆數仍為 6 |

## UI 證據

| Viewport | 螢幕截圖 | 備註 |
|---|---|---|
| 不適用 | 無 | 本專案為 CLI，沒有 UI 變更；以錄製 DOM、JSON 與 live 唯讀確認取代視覺證據 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 無功能性、安全性、隱私或架構阻擋問題 | 無 | 核准 |
| 寫入使用同一 POST 的 `setvalue + click`，且 transport 只重試 GET | 高風險控制 | 已驗證 |
| 工單唯一命中、語意控制項唯一解析、寫入後業務鍵確認及返回清單確認均 fail closed | 高風險控制 | 已驗證 |
| 寫入結果不明與勾稽完成後返回失敗使用不同安全錯誤 | 中 | 已驗證 |
| 三個既有測試依賴未提供的可選錄製 DOM | 低 | 已知、非本次回歸；新錄製 DOM 測試已通過 |

## 安全性與可維護性審查

- 發現的問題：無阻擋問題。
- 輸入：工作單號沿用既有驗證；故障通報號限制為 1–20 個英數字／連字號且首字元為英數字。
- 身分與網路：沿用 `.env`、同源 HTTPS、TLS、目前 session 的 CSRF/page state；沒有新增密鑰或外部 URL。
- 寫入完整性：唯一且完全相符的工單才會進入；不只依賴 HTTP 200，必須在目標表格找到完全相符故障通報號。
- 重試：requests adapter 的 `allowed_methods` 維持只有 GET；寫入 POST 失敗會回報結果不明，不自動重送。
- 隱私：repo 未新增原始 HAR、cookie、token、session ID、完整 response 或瀏覽器依賴。
- 可維護性：重用既有 reader、parser 與 event client；沒有平行 transport 或新依賴。
- 核准建議：核准，進入人工驗收。

## 跳過測試說明

- `tests/test_parser.py`：本機未提供既有多頁故障通報錄製 DOM。
- `tests/test_query_daily_inspection_work_orders_by_vehicle_and_date.py`：本機未提供該既有日檢工單錄製 DOM。
- `tests/test_read_daily_inspection_work_order.py`：本機未提供該既有工作單明細錄製 DOM。
- 本次功能指定的 2026-09-24 勾稽錄製 DOM 存在且整合測試通過，因此上述跳過不阻擋 MMIS-012。

## 殘留風險

- MMIS 權限拒絕的確切 DOM 尚無錄製；目前會 fail closed，不會回報成功。
- 寫入 POST 若已送達但回應遺失，技術上無法由同一程序判定結果；程式會停止並要求人工確認。
- 程式不提供解除勾稽；若需回復遠端資料，由使用者依已授權的 MMIS 人工流程處理。
- 返回清單後的下一筆或批次操作不在本任務範圍。

## 人工驗收

- 2026-09-24：專案使用者回報實際測試正常，MMIS-012 驗收通過。
