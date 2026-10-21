# AI-Ready 任務卡

- 任務：MMIS-057 依結案狀態檢查填寫離線 Excel 備註。
- 上層規格：`feature-spec.md` 第十二階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：從既有 SQLite 匯出可直接辨識處理狀態的 Excel。
- 分軌：後端。
- 前置任務：MMIS-056 已完成。
- 狀態：完成。使用者於 2026-10-21 指定 CSV 規則並要求實作。
- 風險等級：中。本機 Excel 檔案輸出；SQLite 唯讀。

## 目標與情境包

- 目標：離線匯出的備註依 `備註規則.csv` 四筆完整狀態組合填寫。
- 相關檔案：離線匯出入口、共用 XLSX helper、對應測試及工具 README。
- 既有模式：共用 helper 讀取 SQLite 15 欄，離線指令只輸出九欄；字串儲存格強制為文字型別。
- 假設：匹配時以規則文字覆蓋 Excel 備註；未匹配時保留 SQLite 原值。
- 未知事項：無。CSV 的四筆內容已確認。
- 允許變更：上述程式、測試、README、此 Epic 的規格與驗證產出物。
- 不得觸碰：MMIS 查詢、同步指令、SQLite 內容及其他匯出格式。
- 情境預算：讀了專案地圖、匯出入口、共用 helper、CSV、相關測試及前一任務卡；跳過無關的 MMIS 網路流程。

## 契約與驗收

- 六欄順序與 SQLite schema 一致，以 `NULL/0/1` 精確比對四筆規則；近似組合不命中。
- 命中時輸出 CSV 對應文字；未命中時保留原備註。無效布林值拒絕匯出。
- SQLite 前後內容一致；九欄、排序、欄寬、列高、無填色及原同步匯出行為維持。
- 非目標：寫回 SQLite、從 Downloads 動態載入規則、調整 MMIS 狀態判斷。

## 驗證契約

- 暫存 SQLite 涵蓋四筆匹配、三種近似組合、未檢查狀態及既有文字。匯出後讀回工作簿並核對資料庫 SHA-256。
- 執行相關 pytest、Python 編譯與 `git diff --check`；可用時以現有 SQLite 做離線匯出核對。
- UI 螢幕截圖：不適用。此任務是 CLI；以 XLSX 儲存格讀回為證據。
- 殘留風險：固定 15.5 pt 列高可能遮住多行原備註。

## 完成證據

- 變更檔案：離線匯出入口、共用 XLSX helper、匯出測試、README、功能規格及本任務卡。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py -q`：89 passed。
- `python -m compileall -q` 指定變更的 Python 檔案，以及 `git diff --check`：通過。
- 現有 SQLite 離線匯出讀回 5 筆，4 筆命中規則，1 筆保留原備註；資料庫 SHA-256 前後一致。
- 獨立審查未發現正確性或安全性問題；其提出的無效狀態測試缺口已補齊。
- 後續任務：無。
