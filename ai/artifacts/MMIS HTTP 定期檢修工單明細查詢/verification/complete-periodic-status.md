# 驗證報告

## 摘要

- 任務：依單筆主工作單查詢完整定期檢修子工單狀態。
- 結果：通過，待人工驗收。
- 驗證者：Codex，2026-11-05。

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_complete_periodic_inspection_work_order_status.py -q` | 通過 | 初次 6 個測試通過；審查後增加空白狀態測試。 |
| `python -m pytest tests/test_complete_periodic_inspection_work_order_status.py tests/test_query_latest_periodic_inspection_work_order.py tests/test_periodic_inspection_work_order_details.py -q` | 通過 | 相關查詢回歸測試通過。 |
| `python -m pytest -q` | 通過 | 最終 exit 0；部分舊測試因缺外部錄製證據而略過。初次因 `test_architecture.py` 的靜態清單落後而有 2 個失敗，更新清單後通過。 |
| `python -m compileall -q src/mmis_connector/periodic_inspection/status.py tools/mmis_development/query_complete_periodic_inspection_work_order_status.py tests/test_complete_periodic_inspection_work_order_status.py` | 通過 | exit 0。 |
| `git diff --check` | 通過 | 無空白錯誤。 |
| `python -m tools.mmis_development.query_complete_periodic_inspection_work_order_status 115-3A-75840` | 通過 | exit 0；一個 JSON，`count=3`，尾碼 `001`、`002`、`003`，第三筆級別 `TR`。 |
| `python -m tools.mmis_development.query_complete_periodic_inspection_work_order_status 115-2A-74886` | 通過 | exit 0；一個 JSON，`count=2`，尾碼 `001`、`002`。 |
| 對命令提供兩個工作單 | 通過 | exit 1；輸出一個 JSON 用法錯誤。 |

## 錄製與畫面證據

- 錄製目錄：`C:\Docker\maximoFlowRecorder\recordings\2026-11-05_query-overdue-work-orders`。時間線記載 `ZZ_PMWO`、所有記錄、工作單、母工單 `0` 與篩選事件。
- 已檢視 `screenshots/2026-11-05T025511-898.png`。畫面顯示第一筆三筆結果；第二筆的 DOM snapshot 仍是第一筆資料，故第二筆以即時查詢驗證。
- 無產品 UI 變更，無新畫面截圖需求。

## 審查與殘留風險

- 架構：沿用 `MMISSession`、`MaximoEventClient`、動態表頭與分頁 parser。新功能位於 `periodic_inspection`，development tool 只做參數與 JSON 輸出。
- 安全：輸入用既有工作單驗證器；只呼叫唯讀查詢事件；未寫入憑證、cookie、token 或錄製原檔。
- 審查：獨立設計與程式審查未發現阻擋問題；依建議保留合法空白狀態欄並加測試。
- 殘留風險：錄製目錄缺少 `raw.har`，無法對照原始 HTTP response；已用兩筆即時 MMIS 查詢補足結果驗證。其他工作單的 DOM 差異尚未逐一驗證。
- 後續：由使用者驗收 JSON 欄名與兩筆查詢結果。
