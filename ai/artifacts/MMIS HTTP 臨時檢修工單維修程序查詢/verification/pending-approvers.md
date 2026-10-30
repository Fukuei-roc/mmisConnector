# 驗證報告：臨時檢修工單待簽核人

## 摘要

- 任務：CLI JSON 新增 `待簽核人`。
- 結果：通過。
- 驗證者：Codex，2026-10-30。

## 指令與結果

| 指令 | 結果 | 證據 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q` | 通過 | 新錄製 HAR 的 5 筆核簽流程中解析出 4 位目前進行者，核簽中流程會切換頁簽；部分舊錄製檔不在本機，既有測試依原規則跳過。 |
| `python -m pytest -q` | 通過，exit 0 | 全套執行至 100%；缺少舊錄製檔的測試跳過。 |
| `python -m compileall -q src tools` | 通過，exit 0 | 無輸出。 |
| `git diff --check` | 通過，exit 0 | 無空白錯誤。 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-45326` | 通過，exit 0 | `工作單狀態=核簽中`；`待簽核人` 位於狀態與已勾稽故障通報之間，值為何建龍、張春然、蔡林正、蕭昇鴻。 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C2-41266` | 通過，exit 0 | `工作單狀態=工單取消`；`待簽核人=[]`。 |

## UI 證據

不適用。此任務只改 CLI JSON，未修改視覺畫面。

## 審查發現

- 沿用現有 `MMISSession` 和 `MaximoEventClient`，未改憑證、授權或網路邊界。
- 頁簽 ID 動態解析；核簽表格缺欄、分頁不連續或姓名空白時報錯，避免輸出不完整名單。
- 未保存或提交 HAR、cookie、token。

## 殘留風險

- 錄製範例只有一頁核簽流程；跨頁邏輯沿用現有表格分頁模式，尚無即時多頁工單可驗證。
- 舊錄製檔不在本機，相關既有測試依設計跳過。即時兩種狀態查詢已通過。
