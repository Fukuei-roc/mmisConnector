# AI-Ready 任務卡

- 任務：MMIS-058 同步完成後重用獨立 SQLite 匯出器。
- 上層規格：`feature-spec.md` 第十三階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 分軌：後端。
- 前置任務：MMIS-057 已完成。
- 狀態：完成。使用者於 2026-10-21 明確要求實作；獨立審查於同日核准。
- 風險等級：高。同步指令涉及 MMIS 網路與寫入，匯出涉及本機檔案。

## 目標與情境包

- 目標：`--export-xlsx` 在成功同步後由獨立匯出指令產生九欄 Excel。
- 相關檔案：兩個 CLI 模組、`_unclosed_ab_xlsx.py`、兩組 XLSX 測試與工具 README。
- 既有模式：同步器先提交 SQLite；匯出器唯讀 SQLite、驗證 15 欄 schema、輸出九欄工作簿。
- 假設：保留同步指令既有 JSON 結果、失敗狀態與不完整同步時跳過匯出的行為。
- 未知事項：無。
- 允許變更：兩個 CLI 模組、兩組 XLSX 測試、工具 README、本 Epic 規格、任務卡及驗證報告。
- 不得觸碰：MMIS 查詢、SQLite schema、其他使用者工作中的檔案。
- 情境預算：讀取專案地圖、兩個 CLI、匯出 helper 相關段落及對應測試；略過無關查詢細節。

## 契約與驗收

- 同步成功時直接呼叫獨立匯出器 `execute()`，傳入資料庫路徑和本次已保存筆數。
- 同步指令不再直接呼叫 `_unclosed_ab_xlsx.export_xlsx()` 或組裝 Excel 欄位設定。
- 產物採用獨立指令的九欄格式；缺少資料庫、筆數不符或輸出設定錯誤時不留下 Excel。
- 獨立指令可在未執行同步的情況下唯讀匯出既有 SQLite。
- 非目標：變更同步順序、MMIS 查詢與寫入、資料庫內容及 Excel 既有樣式。

## 驗證契約

- 執行兩個指令的離線測試，讀回工作簿檢查欄位、筆數、列高與備註。
- 覆蓋部分成功、SQLite 失敗、匯出失敗與筆數不符。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py -q`。
- `python -m compileall -q tools/mmis_development` 與 `git diff --check`。
- 安全性：匯出器維持唯讀 SQLite，既有公式字串保護仍由 `_unclosed_ab_xlsx.py` 處理。
- UI 螢幕截圖、型別檢查與建置：不適用於此 Python CLI。

## 完成證據

- 變更檔案：同步 CLI、獨立匯出 CLI、兩組 XLSX 測試、工具 README、本 Epic 規格與驗證報告。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py -q`：通過。
- `python -m pytest -q`：完整套件 exit code 0，既有 skip 仍保留。
- `python -m compileall -q tools/mmis_development`、`git diff --check`：通過。
- 實際執行獨立匯出 CLI：既有 SQLite 匯出 5 筆、Excel 九欄、SQLite SHA-256 執行前後一致。
- 已知限制：未執行即時同步 CLI；它會查詢 MMIS，且可觸發故障分析寫入。
- 獨立審查：架構、正確性、安全性與測試範圍均無需修改的發現；實際 `python -m` 子程序驗證已完成。
