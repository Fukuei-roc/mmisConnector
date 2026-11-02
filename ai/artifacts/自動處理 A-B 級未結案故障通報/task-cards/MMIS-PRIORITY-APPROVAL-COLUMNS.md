# AI-Ready 任務卡

## Metadata

- 任務：優先簽核工單報表新增工單類型並依工作單號排序。
- 上層規格：`feature-spec.md` 第二十四階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：在優先簽核報表快速辨識工單類型與查找工單。
- 分軌：後端。
- 前置任務：MMIS-PRIORITY-APPROVAL-XLSX，已完成。
- 狀態：完成。
- 風險等級：中，涉及本機 Excel 與唯讀 MMIS 查詢。
- 人工核准者：使用者本次明確要求實作與驗證。

## 目標

`--export-xlsx` 產生依工作單號排序的兩欄優先簽核報表，支援 1A、C1/C2/C3 與 2A/3A。

## 情境包（Context Pack）

- 相關檔案：`_priority_approval_xlsx.py`、`periodic_inspection/reader.py`、`_unclosed_ab_xlsx.py` 與對應測試。
- 既有模式：從 SQLite JSON 去重、重用單一 MMIS session、使用共用 `read_pending_approvers` 與 `build_workbook`。
- 假設：C 類子單依第二段分類；2A/3A 核簽記錄可由共用讀取器解析。
- 未知事項：正式 MMIS 中是否有符合組長條件的 2A/3A 工單。
- 允許變更的檔案：上述匯出器、定期檢修 Reader、相應測試及本 Epic 文件。
- 不得觸碰：正式 SQLite、MMIS 寫入流程、不相關報表。
- 驗證指令：`python -m pytest -q tests/test_priority_approval_xlsx.py tests/test_periodic_inspection_work_order_details.py`、`python -m compileall -q`、`git diff --check`。
- 情境預算：已讀專案地圖、架構地圖、流程、舊任務卡、目標模組與測試；略過無關查詢模組及 UI。

## 需求與驗收標準

- 兩欄依序為「工單類型」、「工作單號」；工作單號 A 到 Z 排序。
- 1A、C1/C2/C3（含子單）、2A/3A 分類值符合規格；未知類型明確失敗。
- 兩欄使用同一字型、文字格式、對齊與列高；欄寬為 18.3、23.4。
- 2A/3A 只在核簽人符合設定組長時輸出；空清單仍輸出兩個表頭。

## 實作與驗證契約

- 資料契約：輸入為待簽核工單號字串；輸出列為 `(工單類型, 工作單號)`。
- 驗證規則：精確匹配工單號與查詢成功，核簽清單須為字串陣列。
- 錯誤處理：無效工單類型或查詢回應拒絕匯出。
- 身分驗證：沿用既有 MMIS session，不更改權限。
- 遷移與回滾：無資料遷移；回滾只需還原程式變更。
- 單元與整合：暫存 SQLite、替身 Reader、讀回真實 XLSX，檢查資料與樣式；定期檢修 Reader 測試核簽讀取。
- E2E：不執行正式同步，既有流程可能寫入 MMIS。
- 型別檢查：專案未設定；Lint：`git diff --check`；Build：`compileall`。
- 螢幕截圖：無 UI；安全：不記錄憑證或正式資料。

## 完成證據

- 變更檔案：優先簽核匯出器、定期檢修 Reader、兩個測試檔、本 Epic 規格與驗證報告。
- 指令：`python -m pytest -q -ra`、`python -m compileall -q tools/mmis_development/_priority_approval_xlsx.py src/mmis_connector/periodic_inspection/reader.py tests/test_priority_approval_xlsx.py tests/test_periodic_inspection_work_order_details.py`、`git diff --check`。
- 測試結果：完整 pytest exit code 0；暫存 SQLite 匯出並讀回 `1102.xlsx`，檢查排序、兩欄分類、格式及欄寬。
- 已知限制：本機缺少定期檢修錄製 DOM，2A/3A 的實際 MMIS 核簽頁籤尚未以現場回應驗證；正式同步未執行。
- 後續任務：下次授權執行時核對 2A/3A 的 MMIS 回應與輸出。
