# AI-Ready 任務卡

- 目標：完成未派工日檢工單查詢及 SQLite 快照。
- 核准：使用者於 2026-11-04 直接要求本階段實作。
- 風險：高，MMIS 網路、身分驗證及本機資料庫。
- 範圍：新增 `unassigned.py`、對應 development tool 與測試；更新 `.gitignore` 和本 Epic 文件。
- 非目標：重複判定及刪除 MMIS 工單。
- 資料契約：每筆三個來源文字欄，另加本次查詢時間；執行結果預設為空字串。
- 錯誤處理：分頁總數、範圍或資料條件不符時失敗；資料庫交易回滾。
- 驗收與驗證：31 筆跨頁測試、快照替換及回滾測試、實際指令和 SQLite 筆數檢查。
- 情境包：`src/mmis_connector/daily_inspection/query.py`、`not_submitted.py`、既有 SQLite development tool、2026-11-04 錄製摘要及 DOM；跳過與此任務無關的工單寫入流程。錄製摘要顯示 64 筆，但未附 `raw.har`，故以實際 MMIS 查詢補驗。
