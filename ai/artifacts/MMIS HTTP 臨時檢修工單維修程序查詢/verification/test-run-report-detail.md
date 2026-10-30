# 驗證報告：試車子單明細

## 摘要

- 任務：`query_temporary_repair_work_order_detail` 支援 TR 試車子單的 12 欄 JSON。
- 結果：通過。
- 驗證者：Codex，2026-10-30。

## 指令與結果

| 指令 | 結果 | 證據 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q -k recorded_tr_detail_has_distinct_json_contract`（修正前） | 預期失敗 | 解析在「檢修級別缺失或不一致」處停止。 |
| `python -m pytest tests/test_temporary_repair_procedure.py -q`（修正後） | 通過，exit 0 | TR 錄製回放驗證 12 鍵、子單狀態、日期、試車結果與核簽人；同號重複及不同號多筆 TR 查詢均回指定錯誤。部分舊錄製檔不在本機，既有測試依原規則跳過。 |
| `python -m pytest -q` | 通過，exit 0 | 全套執行至 100%；缺少舊錄製檔的測試跳過。 |
| `python -m compileall -q src tools` | 通過，exit 0 | 無輸出。 |
| `git diff --check` | 通過，exit 0 | 無空白錯誤。 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C2-46115-001` | 通過，exit 0 | 12 鍵依指定順序；母單 `115-C2-46115`、子單狀態 `核簽中`、待簽核人張春然與蕭昇鴻、日期 `2026/10/30`、試車結果 `良好`。 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-45326` | 通過，exit 0 | 一般 C1 工單仍有原本 16 鍵，未混入 `母工作單編號`。 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-46055` | 通過，exit 0 | 一般 C1 工單仍有原本 16 鍵，未混入 `母工作單編號`。 |

## UI 證據

不適用。此任務只改 CLI JSON，未修改視覺畫面。

## 審查發現

- 子單與母單狀態會同時出現在「關聯工單」；程式按精確子單號找同區塊狀態。
- 審查發現多筆 TR 結果包含不同子單號時會落到通用錯誤；已補失敗測試並修正為指定錯誤。
- 三個頁簽 target 從初始完整明細解析，避免局部回應缺少其他頁簽。
- 沿用既有 MMIS session、動態 Maximo event 與核簽分頁檢查，未保存 HAR、cookie 或 token。

## 殘留風險

- 錄製範例的核簽流程只有一頁；跨頁仍沿用既有核簽分頁邏輯。
- 部分舊錄製檔不在本機，相關既有測試依設計跳過；指定 TR 與兩筆一般工單已即時查詢通過。
