# 逾期工單 XLSX 匯出驗證報告

## 摘要

- 任務：為逾期工單查詢新增 `--export-xlsx`。
- 結果：通過；2026-11-05 已執行實際 MMIS 查詢並輸出 XLSX。
- 驗證者：Codex；獨立 agent 審查程式、安全性與註解。

## 指令與結果

| 指令 | 結果 |
|---|---|
| `python -m pytest tests/test_overdue_work_orders.py tests/test_complete_periodic_inspection_work_order_status.py tests/test_unclosed_ab_xlsx.py -q -rs` | 47 passed、1 skipped。錄製 DOM 不在本機。 |
| `python -m compileall -q tools/mmis_development/audit_overdue_work_orders.py tests/test_overdue_work_orders.py` | 通過。 |
| `git diff --check` | 通過。 |
| `python -m tools.mmis_development.audit_overdue_work_orders --export-xlsx` | `Status: SUCCESS`，`Records found: 10`，輸出 `工單逾期查詢_程式產生1105.xlsx`。 |
| `openpyxl` 讀回實際 XLSX 與 SQLite 比對 | 九欄標題一致，10 筆資料列全數一致，標題置中、資料靠左，字型大小為 12 點。 |

## 審查與限制

獨立審查發現 Excel 對超過 32,767 字元的儲存格會截短資料。匯出入口已加上長度檢查與不合法控制字元的安全錯誤訊息，測試確認失敗時不產生 XLSX、也不破壞 SQLite。再次獨立審查建議核准。註解審查未發現新增的不必要註解。

實際執行的備註非空資料列為零筆；測試另以非空備註、空白備註及非 2A／3A 資料列驗證完整匯出。未安裝 `ruff`，因此沒有 lint 證據。無 UI 變更，不需螢幕截圖。輸出檔案位於 `.env` 指定的工作區外資料夾，未納入 Git。
