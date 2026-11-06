# MMIS 開發工具指令索引

本頁列出 `tools/mmis_development/` 的 22 個可執行工具。從專案根目錄執行指令，先依根目錄 `README.md` 設定 MMIS 登入用的 `.env`。表格中的通報號、工作單號和車號都是可替換的範例值。

**讀表方式：**「輸入」只列必填命令列參數；「產出」分清終端輸出、本機檔案與 MMIS 寫入。`—` 表示沒有額外參數或檔案。除了表格標明的 SQLite、JSON、Excel 檔案，其餘查詢結果只顯示在終端，不會自動存檔。

## 故障通報

同一模組先列可處理整批或完整資料的工具，再列單項查詢。

| 功能 | 指令 | 附加參數 | 輸入 | 產出 |
|---|---|---|---|---|
| 處理 A/B 級未結案通報 | `python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices` | `--check-analysis-readiness`：對每筆待處理通報檢查分析資料；`--export-xlsx`：另產生兩份 Excel，可同時指定 | 無 | 終端 JSON；重建 `data/unclosed_ab_fault_notices.db`，並維護 `data/a_level_fault_notices_awaiting_closure.db`；符合條件時寫入 MMIS 故障分析與 ATP 分析 |
| 查詢完整通報 | `python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14` | `--ai-analysis`：產生 AI 故障分析及 ATP 分類建議；`--check-analysis-readiness`：以 AI 檢查分析素材是否足夠。兩者互斥 | 通報號 | 終端 JSON：基本資料、結案狀態、段修與 CA 工單、故障分析、ATP 分析及工單素材 |
| 匯出既有 A/B 級資料 | `python -m tools.mmis_development.export_unclosed_ab_fault_notices_from_db` | — | 無；需已有 `data/unclosed_ab_fault_notices.db` | 終端 JSON；從現有 SQLite 產生 `AB級未處理故障通報_程式產生MMDD.xlsx` |
| 查詢 A/B 級未結案清單 | `python -m tools.mmis_development.query_unclosed_fault_notices` | — | 無 | 終端 JSON：新竹機務段 A/B 級未結案通報 |
| 查詢本段未處理清單 | `python -m tools.mmis_development.query_unprocessed_fault_notices` | — | 無 | 終端 JSON：本段未處理通報 |
| 查詢段修工單 | `python -m tools.mmis_development.query_work_orders_linked_to_fault_notice 1150910-14` | — | 通報號 | 終端 JSON：關聯段檢修工單 |
| 查詢 CA 查修工單 | `python -m tools.mmis_development.query_repair_work_orders_linked_to_fault_notice 1150930-09` | — | 通報號 | 終端 JSON：關聯 CA 查修工單 |
| 查詢一般故障分析 | `python -m tools.mmis_development.query_fault_notice_analysis 1150828-12` | — | 通報號 | 終端 JSON：事故現象、處理概況、故障原因、處理情形、改善對策 |
| 查詢 ATP 故障分析 | `python -m tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice 1150210-36` | — | 已勾選 ATP 故障的通報號 | 終端 JSON：故障要因、故障因子、故障項目 |
| 匯出 ATP 分析選項 | `python -m tools.mmis_development.export_atp_fault_analysis_options 1151012-36` | — | 已勾選 ATP 故障的通報號 | 終端 JSON；完整時更新 `data/atp_fault_analysis_options.json`，部分失敗時寫入 `data/atp_fault_analysis_options.partial.json` |

`auto_process_unclosed_ab_fault_notices` 每次都重新查詢並更新 SQLite。預設只對尚未完成一般故障分析的通報執行付費 AI 資料充分性檢查；需要時也會呼叫 AI 產生分析，再寫入 MMIS。`--check-analysis-readiness` 會擴大檢查範圍，增加 API 使用量。`--export-xlsx` 只在同步和處理成功後匯出兩份檔案：`AB級未處理故障通報_程式產生MMDD.xlsx`（含「待簽核工單」，共 10 欄）及 `優先簽核工單_程式產生MMDD.xlsx`。後者會查詢待簽核工單並依 `.env` 的 `MMIS_INSPECTION_GROUP_LEADER` 篩選。獨立的 `export_unclosed_ab_fault_notices_from_db` 只讀取既有 SQLite，只產生第一份 Excel，不重新查詢或修改 MMIS。

`query_fault_notice_full_detail` 不加附加參數時只查詢 MMIS；兩種 AI 參數都需要 `.env` 的 `OPENAI_API_KEY`，會使用付費 API，不寫入 MMIS。

## 日檢工單（1A）

| 功能 | 指令 | 附加參數 | 輸入 | 產出 |
|---|---|---|---|---|
| 清查未送簽核工單 | `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval` | `--export-xlsx`：另產生兩份 Excel | 無 | 終端顯示筆數及路徑；重建 `data/daily_inspection_work_orders_not_submitted_for_approval.db`，標記需通知檢車室的工單 |
| 查詢日檢完整明細 | `python -m tools.mmis_development.query_daily_inspection_work_order_details 115-1A-71815` | — | 日檢工作單號 | 終端 JSON：基本資料、已勾稽通報、檢修記錄、重要事項、檢修人員及記錄完成狀態 |
| 找出重複未派工工單 | `python -m tools.mmis_development.auto_delete_duplicate_daily_inspection_work_orders` | — | 無 | 終端顯示候選工單；重建 `data/auto_delete_duplicate_daily_inspection_work_orders.db`，標記較舊的重複工單 |
| 依車號和日期找工單 | `python -m tools.mmis_development.query_daily_inspection_work_orders_by_vehicle_and_date 717 '>2026/09/23'` | — | 車號、檢修日期條件；PowerShell 中以引號包住 `>` | 終端 JSON：符合條件的日檢工單清單 |
| 查詢工單已勾稽通報 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number 115-1A-70048` | — | 日檢工作單號 | 終端 JSON：已勾稽故障通報 |
| 勾稽故障通報 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number_and_link_fault_notice 115-1A-71002 1150923-36` | — | 日檢工作單號、通報號 | 寫入 MMIS 工單與通報的關聯；終端 JSON 回報確認結果 |
| 取消未派工工單 | `python -m tools.mmis_development.delete_unassigned_daily_inspection_work_order 115-1A-70048` | — | 日檢工作單號 | 符合「執行中未派工」時，以「重複開單」為理由取消 MMIS 工單；終端 JSON 回報確認結果 |

未送簽核清查的 `--export-xlsx` 會產生 `檢車室未填檢修人員日檢工單_程式產生MMDD.xlsx` 和 `未簽核日檢工單清查_程式產生MMDD.xlsx`。第二份收錄未出現在第一份的其他快照資料。重複未派工工具只標記候選，不會取消 MMIS 工單。

「勾稽故障通報」和「取消未派工工單」會修改 MMIS。只在明確核准的受控 Live 驗證或人工單筆操作中執行；如果寫入結果不明，先人工確認，不要直接重送。

## 定期檢修工單（2A／3A）

| 功能 | 指令 | 附加參數 | 輸入 | 產出 |
|---|---|---|---|---|
| 查詢定期檢修明細 | `python -m tools.mmis_development.query_periodic_inspection_work_order_details 115-2A-69254-001` | — | 定期檢修工作單號 | 終端 JSON：基本資料、維修程序、備註非空的檢修記錄及維修情形 |
| 查詢主工單的子工單狀態 | `python -m tools.mmis_development.query_complete_periodic_inspection_work_order_status 115-3A-75840` | — | 定期檢修主工作單號 | 終端 JSON：全部子工單的車號、級別、單號、單位和狀態 |
| 查詢最新 2A／3A 工單 | `python -m tools.mmis_development.query_latest_periodic_inspection_work_order 813` | — | 車組或車號 | 終端 JSON：符合條件且檢修日期最新的一筆工單 |

## 臨時檢修工單

| 功能 | 指令 | 附加參數 | 輸入 | 產出 |
|---|---|---|---|---|
| 查詢臨時檢修明細 | `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-41264` | — | 臨時檢修工作單號 | 終端 JSON：基本資料、已勾稽通報、維修程序及試車報告 |

## 逾期工單

| 功能 | 指令 | 附加參數 | 輸入 | 產出 |
|---|---|---|---|---|
| 清查逾期工單 | `python -m tools.mmis_development.audit_overdue_work_orders` | `--export-xlsx`：另產生全部工單的 `工單逾期查詢_程式產生MMDD.xlsx` | 無 | 終端顯示筆數及備註非空的工單；重建 `data/overdue_work_orders.db`，補查 2A／3A 子工單狀態並寫入備註 |

## Excel 輸出設定

所有 Excel 指令共用 `.env` 的 `UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR`。請填入已存在的**絕對路徑**；程式不會建立資料夾。匯出需要 `openpyxl`。檔名中的 `MMDD` 使用台北日期；若同名檔案已存在，會依序加上 `_2`、`_3`，不覆蓋舊檔。A/B 級同步匯出「優先簽核工單」時，還需要設定 `MMIS_INSPECTION_GROUP_LEADER`。

## 工具範圍與共用程式

這些程式是開發和診斷入口，正式 `mmis-connector` CLI 不會派送到這裡。`src/mmis_connector/` 放登入、Maximo event、資料解析與共用業務邏輯；正式功能不應依賴這些工具。

`__init__.py` 是套件標記。`_support.py` 統一輸出 JSON；`_unclosed_ab_xlsx.py` 共用 Excel 產生和存檔邏輯；`_priority_approval_xlsx.py` 供 A/B 級同步匯出優先簽核清單。這四個檔案沒有獨立的 `python -m` 指令。
