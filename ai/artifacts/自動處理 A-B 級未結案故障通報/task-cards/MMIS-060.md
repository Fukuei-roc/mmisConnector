# AI-Ready 任務卡

## Metadata

- 任務：MMIS-060 待簽核且分析未完成時，Excel 備註填未處理。
- 上層規格：`feature-spec.md` 第十五階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：完成同步後匯出 XLSX。
- 分軌：後端。
- 前置任務：MMIS-058 已完成。
- 狀態：完成。使用者於 2026-10-22 明確指定六欄條件、輸出文字與先查重複。
- 風險等級：中。本機 Excel 檔案輸出；SQLite 唯讀。
- Agent owner：Codex。
- 人工核准者：專案使用者，透過本次明確需求核准。

## 目標與情境包

- 目標：指定狀態組合在 Excel 備註顯示「未處理」。
- 相關檔案：`export_unclosed_ab_fault_notices_from_db.py`、`test_export_unclosed_ab_fault_notices_from_db.py`、工具 README、上層規格。
- 既有模式：`--export-xlsx` 呼叫獨立匯出器；`STATUS_RULES` 依六欄完整組合查表，`annotate_row()` 只改匯出列。
- 假設：命中時覆蓋原備註；未命中時保留原值，沿用既有契約。
- 未知事項：無。指定組合不在既有規則表。
- 允許變更的檔案：匯出器、對應測試、工具 README、本 Epic 規格、任務卡與驗證報告。
- 不得觸碰：MMIS 網路流程、SQLite 原始資料、其他使用者工作中的檔案。
- 情境預算：讀取專案地圖、情境協定、同步匯出路徑、匯出器、既有測試及規格；略過無關的 MMIS 登入與查詢細節。

## 契約與驗收

- 以 `(NULL,0,0,1,0,0)` 精確比對六欄，命中時在 Excel 備註寫「未處理」。
- `(NULL,0,0,0,0,0)` 不命中，保留原備註；原本四條規則維持。
- 依 `1151017-30` 實際 SQLite 值補上 `(0,0,0,1,0,0)`，同樣輸出「未處理」；不改資料充分性檢查流程。
- 不更改 SQLite schema、原始資料、同步順序及 Excel 格式。
- 非目標：改變資料充分性再查詢、MMIS 寫入或其他狀態的語意。

## 驗證契約

- 在暫存 SQLite 製作命中與近似資料，讀回實際 XLSX，核對備註與 SQLite SHA-256。
- 執行匯出與同步相關 pytest、完整 pytest、編譯及 `git diff --check`。
- 安全性：沿用匯出器的 SQLite 唯讀連線、布林值驗證及 Excel 字串文字型別保護。
- UI 螢幕截圖、型別檢查與建置：不適用於此 Python CLI。

## 完成證據

- 見 `verification/MMIS-060.md`。
