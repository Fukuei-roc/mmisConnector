# 驗證報告

## 摘要

- 任務：定期檢修工單先查預設清單，零筆再查所有記錄
- 結果：通過
- 驗證者：Codex，2026-10-13

## 指令與結果

| 指令 | 結果 | 證據 |
|---|---|---|
| `python -m pytest tests/test_periodic_inspection_work_order_details.py -q` | 通過 | 預設命中、零筆 fallback、兩次零筆、非完全相符、原有輸出與分頁案例通過；舊錄製 DOM 缺檔故略過 1 項 |
| `python -m pytest -q -ra` | 通過 | 全套 exit code 0；歷史外部錄製測試依缺檔條件略過 |
| `python -m compileall -q src/mmis_connector/periodic_inspection tests/test_periodic_inspection_work_order_details.py` | 通過 | exit code 0 |
| `git diff --check` | 通過 | exit code 0；僅 Windows 換行提示 |
| `python -m tools.mmis_development.query_periodic_inspection_work_order_details 115-2A-76067-001` | 通過 | exit code 0；預設清單工單 `success=true`、`檢修記錄={"count":0,"records":[]}` |
| `python -m tools.mmis_development.query_periodic_inspection_work_order_details 115-2A-69254-001` | 通過 | exit code 0；預設清單查無後，所有記錄查得 `檢修記錄.count=1` |

## 錄製與 UI 證據

- 新錄製 HAR 確認預設清單查 `115-2A-69254-001` 為 0 筆、查 `115-2A-76067-001` 為 1 筆；切「所有記錄」後前者為 1 筆。
- 實作仍是 HTTP-only CLI，沒有 UI 視覺變更；無截圖驗證要求。

## 審查發現

| 發現 | 風險 | 狀態 |
|---|---|---|
| 只有表格與分頁計數均確認零筆才 fallback；錯誤、不唯一、不相符不重查 | 錯誤結果與不必要重查 | 已測試 |
| fallback 後重新設定工作單篩選；XHR 序號依實際事件前進 | 查到所有記錄中的其他工單 | 即時及離線通過 |
| JSON 產生區塊與檢修記錄解析未變 | 輸出回歸 | 離線及兩張即時工單通過 |
| 沿用同一程序內 MMIS session；未寫入錄製 HAR、cookie 或密鑰 | 身分驗證與網路邊界 | 已檢查 |

## 殘留風險與後續任務

- 原 MMIS-039 使用的明細 DOM 錄製目前不在本機，該可選測試略過；兩張即時工單已驗證新舊查詢範圍。
- 沒有阻擋事項；若需量化延遲改善，可用相同網路環境多次測量兩個範圍。
