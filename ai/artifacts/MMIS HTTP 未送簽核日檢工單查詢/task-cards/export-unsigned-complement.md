# AI-Ready 任務卡

## Metadata

- 任務：同次匯出未簽核日檢工單清查 Excel
- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢
- 上層 User Story：將查詢結果交付檢車室檢視
- 分軌：後端
- 前置任務：`export-xlsx` 已完成
- 狀態：完成，待人工驗收
- 風險等級：中，本次擴充會寫入另一個本機 Excel 檔案
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-04 明確要求實作

## 目標

同次執行 `--export-xlsx` 時，額外輸出未出現在第一份檢車室 Excel 中的其餘日檢工單資料。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py`、`tools/mmis_development/_unclosed_ab_xlsx.py`、`tests/test_query_daily_inspection_work_orders_not_submitted.py`、本 Epic feature spec。
- 既有模式：以 SQLite 快照為來源；第一份 XLSX 由共用 `build_workbook`、`save_workbook` 輸出；快照以「工作單」為唯一鍵。
- 假設：以本次實際產生的第一份 XLSX 之「工作單」欄作排除集合，避免依賴舊檔案或重複推導篩選條件。
- 未知事項：Live MMIS 當下筆數；輸出目錄是否可寫。
- 允許變更的檔案：目標工具、對應測試、MMIS development README、本 Epic 規格／任務卡／驗證報告、Kanban 卡片。
- 不得觸碰：MMIS 查詢條件、資料庫 schema、憑證、其他工具。
- 情境預算備註：讀取目標模組、其測試、共用 XLSX exporter、專案地圖與治理流程；沒有展開其他 MMIS 功能。

## 需求

- 保留原第一份 Excel 的欄位、內容、樣式與命名行為。
- 產生 `未簽核日檢工單清查_程式產生MMDD.xlsx`，欄位依序為車組/車號、工作單、車次、工作單狀態、處理人員、階段核簽人、檢修日期、完工日期、備註欄。
- 欄寬依欄位順序固定為 11.8、17.9、6.5、15.8、10.6、13.2、14.5、14.5、30。
- 從本次完整 SQLite 快照輸出工作單不在第一份 Excel 的所有列，維持快照順序。
- 沿用第一份 Excel 的文字、對齊與換行格式；檔案同名時不可覆寫。

## 驗收標準

- 同次匯出產生兩個檔案，第二份欄位順序及檔名正確。
- 第二份工作單集合與第一份不重複，兩份合併完整覆蓋 SQLite 快照。
- 第二份九欄依指定值設定欄寬。
- 第二份字型、字級、標題與資料對齊、列高符合既有格式。
- 零筆補集仍有標題列；既有匯出與無旗標行為不變。

## 實作備註

- 先從第一份實際產物讀取工作單集合，再從核對筆數的 SQLite 快照投影九欄。
- 沿用既有 XLSX builder 與獨占建立檔案流程，不新增依賴。

## 驗證契約

- 單元測試：雙檔補集、欄位、檔名、字型、對齊與列高。
- 整合測試：目標查詢工具與共用 XLSX 測試。
- E2E 測試：Live MMIS 非必要；本機 XLSX 實際產物可離線驗證。
- 型別檢查：不適用，專案未設獨立指令。
- Lint：不適用，專案未設獨立指令。
- Build：`python -m compileall -q` 目標模組與測試。
- 螢幕截圖：不適用，非 UI。
- 安全性檢查：核對文字儲存格安全、輸出目錄檢查與同名檔防覆寫。

## 完成證據

- 變更的檔案：目標 development tool、對應測試、development README、Epic feature spec、此任務卡、驗證報告、Kanban Epic 與 MMIS-051 卡片。
- 執行過的指令：見 `../verification/export-unsigned-complement.md`。
- 測試輸出：補集匯出 59 passed、2 skipped；欄寬更新 25 passed、2 skipped；compileall 與 `git diff --check` 通過。
- 螢幕截圖：不適用。
- 已知限制：未重跑 Live MMIS；本次實際匯出沿用既有 SQLite 快照。
- 後續任務：人工驗收。
