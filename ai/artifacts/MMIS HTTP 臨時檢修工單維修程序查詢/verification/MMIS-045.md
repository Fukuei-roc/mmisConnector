# 驗證報告

## 摘要

- 任務：臨時檢修工單 JSON 新增工作單並調整輸出排序
- 結果：通過
- 驗證者：Codex，2026-10-14

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q` | 通過 | 指定錄製 DOM/HAR 主工單解析、父子欄位區分與既有案例；部分舊錄製不在本機而略過 |
| `python -m pytest -q` | 通過 | 全套 exit code 0；需要缺失的外部舊錄製之案例略過 |
| `python -m compileall -q src/mmis_connector/temporary_repair tools/mmis_development tests/test_temporary_repair_procedure.py` | 通過 | exit code 0 |
| `git diff --check` | 通過 | exit code 0；只有 Windows 換行提示 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-41264` | 通過 | 即時 JSON 前五鍵順序正確，`工作單` 與查詢號碼同為 `115-C1-41264`，後續欄位及清單成功輸出 |
| `python C:\Users\NMMIS\.codex\skills\mmis-dev-knowledge\scripts\update_mmis_dev_knowledge.py --input "ai\artifacts\MMIS HTTP 臨時檢修工單維修程序查詢\mmis-knowledge-update-MMIS-045.json"` | 通過 | `apiPatterns/maximo-basic-detail-labels-and-visible-date` 已合併；無舊項目停用 |

## UI 證據

CLI JSON 契約變更，無 UI 變更。已對照使用者指定錄製的 DOM 與 HAR；檢修回報 response 含主工單與子單欄位。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 明細初始 AJAX 片段不含工作單標籤；檢修回報 response 才有 | 中 | 已改在既有檢修回報回應解析，無額外 request |
| 同名的子工作單欄位可能為空或另一工單號 | 中 | 依錄製 DOM 順序取主工單，並與查詢號碼完全比對 |
| `work_order` 鍵重新命名可能影響既有 JSON 消費者 | 中 | 已更新功能規格並列為契約變更 |
| 沿用現有登入與唯讀 event；不記錄敏感 session 證據 | 低 | 已檢查 diff |

## 殘留風險

- 其他 MMIS 畫面版本若改變主工單與子單欄位的 DOM 順序，查詢會因號碼不一致而安全報錯；指定錄製與即時工單已驗證。
- 部分舊錄製檔不在本機，相關既有測試由 pytest 略過。

## 後續任務

- 使用 `work_order` 舊鍵的下游消費者需改讀 `queried_work_order_number`。
