# 驗證報告

## 摘要

- 任務：優先簽核工單報表新增類型欄、排序與指定欄寬。
- 結果：離線驗證通過；2A/3A 現場 MMIS 回應待核對。
- 驗證者：Codex。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest -q -ra` | exit code 0 | 完整測試通過；部分需本機錄製 DOM/HAR 的測試按既有條件跳過。 |
| `python -m compileall -q tools/mmis_development/_priority_approval_xlsx.py src/mmis_connector/periodic_inspection/reader.py tests/test_priority_approval_xlsx.py tests/test_periodic_inspection_work_order_details.py` | exit code 0 | Python 編譯通過。 |
| `git diff --check` | exit code 0 | 無空白錯誤。 |

## 活頁簿證據

- `test_deduplicates_and_filters_both_work_order_types_and_matches_style` 從暫存 SQLite 匯出並以 openpyxl 重開 `優先簽核工單_程式產生1102.xlsx`。驗證兩欄順序、1A/2A/C 類標籤、工作單號排序、字型、儲存格文字格式、對齊、列高及 18.3/23.4 欄寬。
- 空清單測試確認仍輸出兩個表頭；子單測試涵蓋 `115-C2-46115-001`。
- 無 UI，螢幕截圖不適用。

## 審查發現

- 架構：沿用原匯出器、共用 Excel 建構器與核簽讀取器；未新增資料庫欄位。
- 安全：工單號沿用既有格式驗證，MMIS 查詢為唯讀，未更動憑證與寫入流程。
- 測試：2A/3A 核簽查詢由替身與共用核簽讀取器測試覆蓋；本機缺少定期檢修錄製 DOM。

## 殘留風險

- 定期檢修頁面若沒有與 1A/C 類相同的「核簽記錄」頁籤，2A/3A 匯出會明確失敗。需用授權的現場唯讀查詢確認。
- 正式同步指令可能寫入 MMIS，故本次沒有重新執行正式同步或改寫既有 `1102.xlsx`。
