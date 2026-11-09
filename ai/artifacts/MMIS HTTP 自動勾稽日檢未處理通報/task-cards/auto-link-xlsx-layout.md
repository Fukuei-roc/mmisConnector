# AI-Ready 任務卡

## Metadata

- 任務：調整自動勾稽 Excel 欄位與版面。
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報。
- 狀態：使用者於 2026-11-09 直接核准實作。
- 風險等級：中。只改匯出結果，不變更資料庫或 MMIS 操作。
- 前置任務：auto-link-xlsx 已實作。

## 情境包與範圍

- 目標：Excel 略過「查詢時間」、轉換 ATP 布林文字、設定固定列高及十欄欄寬。
- 相關檔案：`src/mmis_connector/auto_link/xlsx.py`、`tests/test_auto_link_xlsx.py`、既有功能規格與驗證報告。
- 既有模式：匯出器以唯讀 SQLite 取得 `fault_notices` 全欄，再建立 openpyxl 工作表；`RESULT_COLUMNS` 定義資料庫欄序。
- 允許變更：匯出器、對應測試、規格與驗證紀錄。
- 不得觸碰：SQLite schema、MMIS 查詢與勾稽流程、其他 Excel 匯出器。
- 假設與未知事項：固定列高優先於自動換行高度；無待釐清事項。
- 驗證：針對性及完整 pytest、compileall、pip check、diff check、實際 Excel 欄位／格式檢查。
- 情境預算：已讀匯出器、對應測試、舊版欄寬範例和 Ready/Done；未擴大搜尋無關 MMIS 頁面。

## 驗收標準

- Excel 只有後 10 欄，SQLite 仍保留 11 欄與原資料。
- `ATP故障` 的 `true`、`false` 顯示為 `Y`、`N`。
- 第一列高度 16，其餘列高度 15.5。
- 欄寬依序為 6.5、11.8、14.5、10.6、10.4、73.6、5.7、14.9、17.9、23.6。
- 離線驗證不呼叫 MMIS。
