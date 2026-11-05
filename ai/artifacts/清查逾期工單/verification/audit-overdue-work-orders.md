# 清查逾期工單驗證報告

## 變更

- 新增 HTTP 逾期工單查詢、SQLite 快照工具與測試。
- 開發工具 README 新增執行指令；`.gitignore` 排除含人員資料的本機資料庫。
- `data/overdue_work_orders.db` 已於本機建立，並由每次成功查詢重建。

## 執行結果

| 指令 | 結果 |
|---|---|
| `python -m pytest tests/test_overdue_work_orders.py -q` | 4 passed；涵蓋錄製頁、可攜式雙頁查詢、覆蓋與失敗回滾。 |
| `python -m compileall -q src/mmis_connector/overdue_work_orders.py tools/mmis_development/audit_overdue_work_orders.py tests/test_overdue_work_orders.py` | 通過。 |
| `git diff --check` | 通過。 |
| `python -m tools.mmis_development.audit_overdue_work_orders` | `Status: SUCCESS`，`Records found: 10`。 |
| SQLite `PRAGMA table_info` 與聚合查詢 | 九欄順序符合需求；10 筆、10 個唯一工單編號、0 筆非空備註。 |

`python -m ruff check` 無法執行，環境未安裝 `ruff`。本任務沒有 UI 變更，無螢幕截圖。Live 查詢只讀取 MMIS；寫入範圍限於本機資料庫。若來源欄位或分頁不完整，程式報錯並保留前次成功快照。錄製 HAR 與登入資料未納入程式或版本控制。

## 殘留限制

資料內容以 MMIS 該頁當次結果為準。錄製頁說明逾期統計每日中午更新一次，因此查詢時間不等於來源統計時間。`.gitignore` 排除資料庫，換機時需重新執行命令建立快照。
