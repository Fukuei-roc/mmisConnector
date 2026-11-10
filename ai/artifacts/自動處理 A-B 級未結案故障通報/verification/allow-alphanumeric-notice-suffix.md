# 英數通報號故障驗證

- 來源：`run_daily_work.bat` 結果顯示 A/B 級同步 `records_fetched=37`、`records_skipped_waiting=29`、`records_loaded=8`、`detail_records_processed=0`、`snapshot_saved=true`，錯誤為通報號格式不符。
- 唯讀檢查 `data/unclosed_ab_fault_notices.db`：8 筆快照第一筆為 `1151109-B0`。
- 修正前：`python -m pytest tests/test_read_fault_notice_analysis.py -q -k letter_in_suffix`，1 failed，`normalize_fault_notice(" 1151109-B0 ")` 拋出 `MMISClientError`。
- 修正後：`python -m pytest tests/test_read_fault_notice_analysis.py tests/test_fault_notice_full_detail.py tests/test_auto_process_unclosed_ab_fault_notices.py -q`，通過，3 skipped（原有錄製資料測試）；唯讀快照檢查顯示 `snapshot_rows=8 accepted=8`。
- 全套回歸：`python -m pytest -q`，退出碼 0；`git diff --check`，退出碼 0。
- 獨立審查：確認格式限制仍排除標點與過長尾碼，明細的唯一筆及完全相符檢查保留；未發現正確性或安全性問題。
- 安全性：限定七位 ASCII 數字、連字號、兩位 ASCII 英數字；唯一筆及完全相符檢查保留。未執行即時 MMIS 查詢或寫入。
- 殘留風險：本地無法證實 MMIS 當下的明細與 AI 分析結果，故尚未宣稱整段批次完成。
