# AI-Ready 任務卡

- 任務：MMIS-056 移除離線 Excel 的三條狀態填色規則。
- 上層規格：`feature-spec.md` 第十一階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：離線 Excel 顯示原始備註，不依狀態填色。
- 分軌：後端。
- 前置任務：MMIS-055 已完成。
- 狀態：完成。人工核准者為使用者，於 2026-10-21 明確要求移除三條規則。
- 風險等級：中。本機 Excel 匯出，SQLite 唯讀。

## 目標與情境包

- 目標：離線 Excel 不自動填色或追加備註。
- 相關檔案：離線匯出入口、共用 XLSX helper、兩支 XLSX 測試與工具 README。
- 既有模式：共用 helper 讀取完整 15 欄並投影九欄；僅離線指令傳入逐列裝飾回呼。
- 假設：第一條附帶的備註追加也隨該規則移除。既有 SQLite 備註保留。
- 未知事項：無。
- 允許變更：離線指令、共用 helper 的未使用裝飾入口、相關測試、README 和本 Epic 產出物。
- 不得觸碰：原同步指令、SQLite 內容、MMIS 查詢及其他匯出樣式。
- 情境預算：只讀裝飾入口、唯一呼叫、相關測試與上一張任務卡；略過 MMIS 網路流程。

## 契約與驗收

- 原本三種條件及其他狀態組合均不使 Excel 儲存格有填滿色。
- Excel 備註與 SQLite 原值一致，不追加「段檢修工單等候簽核」。以公式開頭的原備註仍為文字型別。
- 其餘九欄、排序、欄寬、列高及對齊維持現有設定。原同步 XLSX 不變。
- 非目標：刪除 SQLite 原備註、修改 MMIS 或調整其他 Excel 版面。

## 驗證契約

- 使用涵蓋原三條條件的暫存資料庫匯出；讀回所有儲存格的填滿色與備註，核對資料庫 SHA-256。
- 對現有 SQLite 實際執行離線指令並讀回；執行相關 pytest、compileall 及 `git diff --check`。
- UI 螢幕截圖：不適用於此 CLI；以工作簿樣式讀回作證據。
- 已知限制：固定 15.5 pt 列高仍可能使多行備註在 Excel 畫面中顯示不全。

## 完成證據

- 變更檔案：離線匯出入口、共用 XLSX helper、離線測試、README、本 Epic 規格與任務卡。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py`：88 passed。
- `python -m compileall -q tools/mmis_development tests/test_export_unclosed_ab_fault_notices_from_db.py` 與 `git diff --check`：通過。
- 實際匯出現有 SQLite 五筆資料後讀回，確認全部儲存格沒有填滿色，Excel 備註與 SQLite 原值逐筆一致；資料庫 SHA-256 前後一致。
- 獨立唯讀審查未發現問題。後續任務：由使用者檢視 Excel 並提出後續格式需求。
