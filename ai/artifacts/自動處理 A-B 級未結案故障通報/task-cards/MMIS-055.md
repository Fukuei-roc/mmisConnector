# AI-Ready 任務卡

- 任務：MMIS-055 依結案狀態設定離線 Excel 通報號填色並追加備註。
- 上層規格：`feature-spec.md` 第十階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：用離線 Excel 辨識待簽核、待分析及資料不足通報。
- 分軌：後端。
- 前置任務：MMIS-054 已完成。
- 狀態：完成。人工核准者為使用者，於 2026-10-21 指定三種條件與備註規則。
- 風險等級：中。本機檔案匯出，SQLite 唯讀。

## 目標與情境包

- 目標：依原資料庫狀態在離線 Excel 的「通報號」欄填色，第一種條件另追加備註。
- 相關檔案：`export_unclosed_ab_fault_notices_from_db.py`、`_unclosed_ab_xlsx.py`、兩支 XLSX 測試、README。
- 既有模式：先讀取完整 15 欄，排序後投影九欄，再建立工作簿；原同步匯出使用共用 helper 的預設設定。
- 假設：使用者的 `fasle` 表示 `false`；三條規則按列出順序判定。淺綠、橄欖綠、黃採 `#92D050`、`#C4D79B`、`#FFFF00`（前兩色依使用者後續指示修正）。
- 未知事項：無。
- 允許變更：離線指令、共用 XLSX helper 的可選逐列裝飾入口、相關測試、README 和本 Epic 產出物。
- 不得觸碰：原同步指令、SQLite 內容、MMIS 查詢及無關程式。
- 情境預算：只讀匯出入口、helper、相關測試與現有 SQLite 狀態欄樣本，略過 MMIS 網路流程。

## 契約與驗收

- 第一項狀態條件成立時，通報號填淺綠，備註若已有文字則換行追加「段檢修工單等候簽核」，否則直接填入。
- 第二項狀態條件成立時，通報號填橄欖綠；第三項成立時填黃；其餘不填色。
- 第一項與第三項同時成立時，採第一項。備註字串維持 Excel 文字型別，避免公式執行。
- 不輸出六個狀態欄，不回寫 SQLite，不修改原同步 XLSX。
- 非目標：改動查詢、排序、欄寬、列高、MMIS 或資料庫 schema。

## 驗證契約

- 暫存 SQLite 測試三色、狀態不成立、重疊優先序、原備註保留和排序後的列對應。
- 讀回 XLSX 核對填滿色、備註及公式安全；比較資料庫 SHA-256。
- 對現有 SQLite 實際執行離線 CLI，核對輸出；執行相關 pytest、compileall 和 `git diff --check`。
- 用原同步匯出測試確認預設工作簿的「通報號」不新增填色。
- UI 螢幕截圖：不適用於此 CLI，以工作簿樣式讀回作證據。
- 已知限制：使用固定 15.5 pt 列高，追加的備註可能在 Excel 視窗中顯示不全，儲存格仍保留完整文字。

## 完成證據

- 變更檔案：離線指令、共用 XLSX helper、兩支 XLSX 測試、README、本 Epic 規格與任務卡。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py`：88 passed。
- `python -m compileall -q tools/mmis_development tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py` 與 `git diff --check`：通過。
- 暫存 SQLite 測試三色、排除條件、重疊優先序、既有備註換行、公式文字安全和資料庫未變。
- 現有 SQLite 實際匯出 5 筆；通報 `1151017-30` 填黃，其餘未符合新填色條件；資料庫 SHA-256 前後一致。
- 獨立唯讀審查未發現需修改的問題。後續任務：由使用者檢視 Excel 並提出後續格式需求。
- 色碼修正後，`python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py`：23 passed；測試讀回 XLSX，確認淺綠為 `#92D050`、橄欖綠為 `#C4D79B`。
