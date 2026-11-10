# 修正 A/B 級同步的英數通報號

- 目標：讓 MMIS 回傳的 `1151109-B0` 能進入明細查詢，保留完整比對與其他格式限制。
- 使用者行為：`run_daily_work.bat` 的 A/B 級同步不因合法英數尾碼在本機驗證階段失敗。
- 範圍：共用通報號格式驗證與對應回歸測試；不修改批次重試、SQLite schema 或 MMIS 寫入流程。
- 相關檔案：`src/mmis_connector/fault_notices/reader.py`、`tests/test_read_fault_notice_analysis.py`。
- 既有模式：所有通報明細讀寫共用 `normalize_fault_notice`，讀取後再以完整通報號確認唯一資料。
- 已確認：使用者確認 `1151109-B0` 是有效通報號；本機快照已保存此值。
- 未知事項：修正後的即時 MMIS 明細查詢及後續 AI、Excel 流程是否成功。
- 驗收標準：英數尾碼通過；不合法長度或字元仍遭拒；現有通報號測試通過；快照 8 筆通報號都能通過格式驗證。
- 非目標：跳過來源通報、擴充通報號總長度、執行即時 MMIS 遠端寫入。
- 風險等級：中；共用輸入驗證會影響明細查詢與分析寫入，但既有精確比對不變。
- 驗證：`python -m pytest tests/test_read_fault_notice_analysis.py tests/test_fault_notice_full_detail.py tests/test_auto_process_unclosed_ab_fault_notices.py -q`；唯讀檢查 SQLite 快照 8 筆。
- 人工核准狀態：使用者於 2026-11-10 明確要求理解架構後實作與驗證此故障。
- 情境預算：讀專案地圖、架構地圖、搜尋指南、工作流程、錯誤來源與批次編排；未展開其他 MMIS 功能模組。
