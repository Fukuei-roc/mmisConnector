# 驗證報告

- `python -m pytest tests/test_unassigned_daily_inspection_work_orders.py -q`：2 passed。
- `python -m compileall -q src/mmis_connector/daily_inspection/unassigned.py tools/mmis_development/auto_delete_duplicate_daily_inspection_work_orders.py`：通過。
- `python -m tools.mmis_development.auto_delete_duplicate_daily_inspection_work_orders`：`Records found: 64`。
- SQLite 直接查詢：64 列，五欄為車組/車號、工作單、預計檢修(進廠)日、查詢時間、執行結果。
- 2026-11-04 修改預設值後重跑：`Records found: 64`；直接查詢 SQLite 共 64 列，64 列的執行結果均為空字串。
- `git diff --check`：通過。
- 殘留風險：錄製資料缺少 raw.har；實際 64 筆查詢已通過，但尚未驗證 MMIS 分頁期間資料變動的情況。下階段需定義重複判定與刪除規則。
