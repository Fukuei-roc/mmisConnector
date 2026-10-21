# AI-Ready 任務卡

- 任務：MMIS-054 指定離線匯出欄寬與三級排序。
- 上層規格：`feature-spec.md` 第九階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：用離線指令預覽指定欄寬與資料順序。
- 分軌：後端。
- 前置任務：MMIS-053 已完成。
- 狀態：完成。人工核准者為使用者，於 2026-10-21 明確指定欄寬與排序。
- 風險等級：中。本機檔案匯出，SQLite 唯讀。

## 目標與情境包

- 目標：離線 Excel 九欄使用指定欄寬，全部資料依事故等級、發生日期、車組/車號遞增排序。
- 相關檔案：`export_unclosed_ab_fault_notices_from_db.py`、`_unclosed_ab_xlsx.py`、離線匯出測試及 README。
- 既有模式：共用 helper 讀取並驗證完整 15 欄 SQLite schema，再投影九欄建立工作簿；原同步指令使用預設匯出格式。
- 假設：發生日期為補零的 `YYYY/MM/DD` 字串，文字遞增順序等於日期先後；排序鍵相同時保留資料庫順序。
- 未知事項：無。
- 允許變更：離線指令、共用 XLSX helper 的可選設定、相關測試、README 和本 Epic 產出物。
- 不得觸碰：原同步指令、SQLite 內容、MMIS 查詢及無關程式。
- 情境預算：只讀匯出入口、helper、相關測試與實際日期樣本，略過 MMIS 網路流程。

## 契約與驗收

- 九欄寬度依序為 6.5、11.8、14.5、10.6、10.6、70、10.6、14.9、40。
- 排序優先序為「事故等級」A 到 Z、「發生日期」A 到 Z、「車組/車號」A 到 Z。空值排在非空值後，完全相同的排序鍵保留原順序。
- 其餘離線樣式維持 MMIS-053 的設定；原同步 XLSX 預設格式維持原狀。
- 非目標：更動原資料庫、日期原值、MMIS 查詢、檔名及輸出資料夾設定。

## 驗證契約

- 用刻意打亂順序的暫存 SQLite 測試三級排序與同鍵穩定性；讀回 XLSX 核對九個欄寬。
- 對現有 SQLite 實際執行離線 CLI，讀回欄寬與排序，核對資料庫 SHA-256 未變。
- 執行相關 pytest、compileall 和 `git diff --check`；以既有同步匯出測試驗證預設格式。
- UI 螢幕截圖：不適用於此 CLI，以工作簿內容與樣式讀回作證據。
- 已知限制：若未來日期資料未補零，文字遞增排序不一定等於日期先後；現有資料採補零格式。

## 完成證據

- 變更檔案：離線指令、共用 XLSX helper、離線測試、README、本 Epic 規格與任務卡。
- `python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py`：87 passed。
- `python -m compileall -q tools/mmis_development tests/test_export_unclosed_ab_fault_notices_from_db.py` 與 `git diff --check`：通過。
- 實際從現有 SQLite 匯出 5 筆；openpyxl 讀回九欄寬度為 6.5、11.8、14.5、10.6、10.6、70、10.6、14.9、40，資料依指定三級鍵遞增排序。
- SQLite SHA-256 前後一致；原同步指令檔案無差異。獨立唯讀審查未發現需修改的問題。
- 後續任務：由使用者檢視 Excel 並提出後續格式需求。
