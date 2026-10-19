# 功能規格書

## Metadata

- 功能：Auto Process Unclosed AB Fault Notices，第一階段
- 負責人：專案使用者
- 狀態：人工已核准（2026-10-19 任務指示）
- 風險等級：高（本機資料庫全量覆蓋）

## 問題

需要建立可重跑的 A/B 級未結案故障通報本機 snapshot，供後續階段使用。

## 使用者

執行 Development Tool 的 MMIS Connector 使用者。

## 目標

- 重用既有未結案查詢，將八個基本欄位寫入固定 SQLite 資料表。
- 成功時全量替換；查詢、驗證或寫入失敗時保留舊資料。

## 非目標

- 完整明細、工單、AI、六個結案狀態檢查、備註填寫、歷史保存、MMIS mutation、Production CLI。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 建立 A/B 級未結案通報 snapshot | 身為開發工具使用者，我想取得本次完整查詢快照，以便後續逐階段處理 | 15 欄 schema、8 欄來源資料、7 欄 NULL；成功全量覆蓋，失敗保留舊資料 |

## 使用者旅程

```text
執行零參數 Python module → 完整查詢及驗證 → SQLite transaction 全量覆蓋 → stdout JSON summary
```

## 功能需求

- WHEN 既有 `UnclosedFaultNoticeQuery` 回傳成功、正確 query 與 filters 且 count 等於 records 長度，THE SYSTEM SHALL 驗證所有基本欄位並儲存。
- WHEN 有缺欄、無通報號、重複號、非 A/B 等級或型別錯誤，THE SYSTEM SHALL 拒絕整批。
- WHEN 結果成功且為空，THE SYSTEM SHALL 清空既有列。
- WHEN 查詢或 transaction 失敗，THE SYSTEM SHALL 保留舊列。

## 畫面

無 UI。

## 資料與 API

- 輸入：既有 Query 的 `success/query_name/filters/count/records` dict。
- 輸出：`data/unclosed_ab_fault_notices.db` 與 stdout JSON summary。
- 驗證：query 身分、筆數、八欄、A/B、通報號唯一與 SQLite schema。
- 錯誤：exit code 1；JSON 說明原因、transaction、rollback 與舊資料狀態。

## 安全性與隱私

- 身分驗證：沿用既有 `MMISSession`；不新增憑證處理。
- 權限：只使用唯讀 MMIS 查詢。
- 敏感資料：JSON summary 不包含逐筆通報或認證資訊。
- 濫用情境：不完整查詢或錯誤 schema 不得清空既有資料。

## 驗收標準

- 15 欄依指定順序；`通報號` 為 `TEXT PRIMARY KEY NOT NULL`。
- ATP 布林依 true/false/null 對應 1/0/NULL，七個預留欄位永遠 NULL。
- 舊列、舊預留欄位內容在下一次成功同步後消失。
- 資料庫相對專案根目錄定位；不修改其他 data 檔案或 Production CLI。

## 驗證計畫

- 單元測試：查詢結果驗證、schema、NULL、全量覆蓋與錯誤路徑。
- 整合測試：mock Query + 暫存 SQLite；既有查詢與 Development Tool 回歸。
- E2E：本階段不執行 Live MMIS。
- 視覺：不適用。
- 手動：檢查 diff、README 與指令輸出。
