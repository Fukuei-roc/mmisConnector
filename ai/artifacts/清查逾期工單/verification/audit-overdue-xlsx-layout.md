# 逾期工單 XLSX 版面與排序驗證報告

## 摘要

- 任務：固定逾期工單 Excel 的列高、九欄欄寬與三層排序。
- 結果：通過；2026-11-05 實際命令輸出 `工單逾期查詢_程式產生1105_3.xlsx`。
- 驗證者：Codex；另有獨立 agent 進行唯讀審查。

## 指令與結果

| 指令 | 結果 |
|---|---|
| `python -m pytest -o addopts= tests/test_overdue_work_orders.py tests/test_complete_periodic_inspection_work_order_status.py tests/test_unclosed_ab_xlsx.py -ra` | 50 passed、1 skipped；本機錄製 DOM 不存在。 |
| `python -m compileall -q tools/mmis_development/audit_overdue_work_orders.py tests/test_overdue_work_orders.py` | 通過。 |
| `git diff --check` | 通過。 |
| `python -m ruff check tools/mmis_development/audit_overdue_work_orders.py tests/test_overdue_work_orders.py` | 無法執行；環境未安裝 `ruff`。 |
| `python -m tools.mmis_development.audit_overdue_work_orders --export-xlsx` | `Status: SUCCESS`，`Records found: 10`，產生 `工單逾期查詢_程式產生1105_3.xlsx`。 |
| `openpyxl` 讀回產出的 XLSX 並與 SQLite 比對 | 九欄一致，10 筆資料依三層文字鍵排序後全數一致；欄寬為 10.6、10.6、17.9、15.8、8.1、14.5、14.5、10.6、40；第 1 列高 16，其餘列高 15.5。 |

## 審查與限制

獨立審查未發現需修改項目。排序只作用於匯出前的記憶體資料列，測試確認 SQLite 內容與列順序不變。逾期天數欄是文字，A 到 Z 排序時 `10` 排在 `2` 前。固定列高 15.5 可能使多行備註在 Excel 中無法完整顯示；這符合本次指定高度。

本機錄製 DOM 測試因來源檔案不存在而略過。無前端 UI 變更，不需螢幕截圖。輸出檔案位於 `.env` 指定資料夾，未納入 Git。
