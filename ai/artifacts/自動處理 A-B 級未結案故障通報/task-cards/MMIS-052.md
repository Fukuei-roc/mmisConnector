# AI-Ready 任務卡

- 任務：MMIS-052 從既有 SQLite 離線匯出 XLSX。
- 上層規格：`feature-spec.md` 第七階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：在修改匯出格式前，先建立不會觸發同步的測試指令。
- 分軌：後端。
- 前置任務：MMIS-049 已完成。
- 狀態：完成。人工核准者為使用者，於 2026-10-21 明確要求建立此程式。
- 風險等級：中。讀取本機資料庫並寫入 XLSX，不連線 MMIS。

## 目標與情境包

- 目標：從現有 `data/unclosed_ab_fault_notices.db` 產生與 `--export-xlsx` 相同格式的 Excel。
- 相關檔案：`auto_process_unclosed_ab_fault_notices.py`、`_unclosed_ab_xlsx.py`、工具 README 與 XLSX 測試。
- 既有模式：`export_xlsx()` 以 SQLite 唯讀連線讀取固定欄位，檢查 schema 後建立工作簿。
- 假設：以原指令的 `COLUMNS` 和 `DETAIL_CHECK_FIELDS` 為欄位契約；沿用既有環境變數設定。
- 未知事項：後續要修改的具體 Excel 格式，留待下一張任務卡。
- 允許變更：獨立匯出指令、該指令測試、工具 README、本 Epic 規格與驗證產出物。
- 不得觸碰：原同步指令、SQLite 內容、MMIS 與無關程式。
- 情境預算：只讀取專案地圖、匯出 helper、原指令的匯出呼叫與相關測試；略過無關的 MMIS 查詢實作。

## 契約與驗收

- 不接受參數。成功時輸出包含筆數與檔案路徑的 JSON，exit code 為 0。
- 使用資料庫既有 15 欄，輸出格式與原 `--export-xlsx` 一致。
- 不執行原指令的 `execute()`、`main()` 或 MMIS 查詢。
- 資料庫不存在時非零結束，不建立資料庫或 Excel。
- 非目標：調整 Excel 格式、同步資料、修改 MMIS 或資料庫 schema。

## 驗證契約與證據

- 暫存資料庫測試匯出內容、布林值、缺少資料庫與無效參數。
- 對現有資料庫實際執行 CLI，以 openpyxl 讀回工作表與筆數，比對匯出前後資料庫 SHA-256。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py`：21 passed。
- `python -m compileall -q tools/mmis_development/export_unclosed_ab_fault_notices_from_db.py` 與 `git diff --check`：通過。
- UI 螢幕截圖、型別檢查與建置：不適用於此 Python CLI。
- 安全性：SQLite 以唯讀 URI 開啟；既有 helper 將字串儲存為文字，避免 Excel 公式執行。
- 已知限制：本指令使用原匯出模組的環境設定，輸出資料夾必須已存在。
- 後續任務：依使用者接下來提供的格式要求修改 XLSX 格式。
