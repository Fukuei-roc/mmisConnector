# 驗證報告 MMIS-BATCH-APPROVAL-OUTPUT

- 變更：CLI 依序輸出核簽前完整待簽數、本次非零已簽核數、最後完整待簽數與 `全部為零`。最後仍有待簽工單時先顯示數量，再以非零代碼結束。
- `python -m pytest tests/test_auto_batch_approve_output.py tests/test_batch_approval.py -q`：結束碼 0，涵蓋三段輸出順序、核簽前即輸出、零值過濾及最後非零時的錯誤。
- `$env:PYTHONPATH = (Join-Path (Get-Location) 'src'); python -m pytest -q`：結束碼 0。直接在隔離工作樹執行 `python -m pytest -q` 會有一個與本變更無關的路徑斷言失敗，因 editable package 仍指向主工作區。設定工作樹的 `src` 後全套通過。
- 在隔離工作樹執行 CLI 入口，先以 `load_dotenv` 載入主工作區忽略版控的 `.env`：結束碼 0。核簽前及最後複查的 17 類待簽數全為 0，本次已簽核段為 `{}`，最後 `全部為零` 為 `true`。
- `git diff --cached --check`：結束碼 0。

## 審查與限制

- 核簽事件仍由原有 `approve_all_pending` 處理。最後查詢重新切換批次核簽 app，不以初始數或核簽數推算。
- 目前無待簽工單，實際寫入路徑的本次輸出無法驗證；正值及最後非零情境由測試涵蓋。既有核簽流程曾完成真實寫入驗收。
- CLI stdout 現在是依序輸出的三個 JSON 物件，不是單一 JSON 文件。呼叫端若解析 stdout，須依序讀取物件。
- 不新增憑證儲存或日誌；輸出僅含類別及數量。高風險人工審查依原任務流程執行。
