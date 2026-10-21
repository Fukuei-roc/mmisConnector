# AI-Ready 任務卡

- 任務：MMIS-053 調整離線匯出 Excel 欄位與對齊。
- 上層規格：`feature-spec.md` 第八階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：用離線指令預覽所需的 Excel 格式。
- 分軌：後端。
- 前置任務：MMIS-052 已完成。
- 狀態：完成。人工核准者為使用者，於 2026-10-21 明確指定格式。
- 風險等級：中。本機檔案匯出，資料庫唯讀。

## 目標與情境包

- 目標：離線指令匯出九欄、固定列高 15.5 pt，所有儲存格垂直靠上。
- 相關檔案：`export_unclosed_ab_fault_notices_from_db.py`、`_unclosed_ab_xlsx.py`、兩支匯出測試與工具 README。
- 既有模式：共用 helper 先核對 15 欄 SQLite schema，再建立單一工作表；原同步指令沿用預設格式。
- 假設：六個省略欄位為 `DETAIL_CHECK_FIELDS`，保留欄位依資料庫原順序排列。
- 未知事項：無。
- 允許變更：離線指令、共用 XLSX helper 的可選設定、相關測試、工具 README 與本 Epic 產出物。
- 不得觸碰：原同步指令、資料庫內容、MMIS 查詢與無關程式。
- 情境預算：只讀匯出入口、helper、相關測試與上一張任務卡，略過 MMIS 網路流程。

## 契約與驗收

- 離線工作表依序輸出 `車次`、`車組/車號`、`發生日期`、`事故等級`、`ATP故障`、`故障現象`、`狀態`、`通報號`、`備註`。
- 表頭與資料列的列高均為 15.5 pt，每一個儲存格的垂直對齊為 top。
- 原同步指令的 XLSX 保持 15 欄及既有列高與對齊。
- 不變更資料庫或重新查詢 MMIS。
- 非目標：更動原同步資料、檔名、輸出資料夾設定及其他樣式。

## 驗證契約

- 單元與整合測試：離線及原匯出測試，讀回工作簿核對兩種格式。
- 實際執行：對現有 SQLite 離線匯出，讀回九欄、列高與對齊，比較資料庫 SHA-256。
- 型別檢查與建置：不適用於本 Python CLI。執行 compileall 與 `git diff --check`。
- UI 螢幕截圖：不適用；以 XLSX 工作簿內容和樣式讀回為驗證依據。
- 安全性檢查：SQLite 唯讀；字串維持文字型別，避免 Excel 公式執行。
- 已知限制：固定列高可能讓多行長文字在 Excel 視窗中只顯示部分內容，儲存格完整文字仍保留。

## 完成證據

- 變更檔案：`_unclosed_ab_xlsx.py`、`export_unclosed_ab_fault_notices_from_db.py`、離線測試、工具 README、本 Epic 規格與任務卡。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py`：86 passed。
- `python -m compileall -q tools/mmis_development tests/test_export_unclosed_ab_fault_notices_from_db.py` 與 `git diff --check`：通過。
- 實際離線匯出現有資料庫後讀回：5 筆、9 欄，六列高度均為 15.5 pt，全部儲存格垂直對齊為 top；資料庫 SHA-256 前後一致。
- 後續任務：由使用者檢視目前 Excel，提出下一輪格式需求。
