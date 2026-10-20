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

## 第二階段：只查詢首筆完整通報（2026-10-20）

- 使用者要求保留既有 15 欄 snapshot，成功儲存後只查詢本次來源結果第一筆通報，不處理後續筆數。
- 直接呼叫 `query_fault_notice_full_detail.execute()`；核對通報號及六欄布林／NULL 型別，以單筆 SQLite transaction 回填；備註及其他通報的檢查欄位維持 `NULL`。
- 預設模式沿用完整通報查詢的非 AI 契約：第一欄 `Sufficient Data for Fault Analysis` 為 `NULL`，其餘五欄為布林值。明確加 `--check-analysis-readiness` 才呼叫付費 OpenAI 並要求第一欄為布林值；不執行 `--ai-analysis`。
- 明細查詢或更新失敗時，已成功建立的完整 snapshot 保留，錯誤 JSON 標示 snapshot 與單筆更新階段；不回滾整個 snapshot。
- 此增量不改變第一階段已完成任務卡 MMIS-045 的歷史驗證紀錄。

## 第三階段：逐筆查詢並保存等候結案 A 級通報（2026-10-20）

- 英文名稱：A-Level Fault Notices Awaiting Closure；獨立資料庫 `data/a_level_fault_notices_awaiting_closure.db`，資料表 `a_level_fault_notices_awaiting_closure`。
- 等候結案庫只有 `通報號`（TEXT PRIMARY KEY NOT NULL）與 `新增日期`（TEXT NOT NULL）；新增日期為當下台北時間的 ISO 日期時間，不因重跑改寫。
- 本次 MMIS 清單仍須完整查詢與驗證。讀取既有等候結案通報號後，從主 snapshot 排除；餘下全部通報依來源順序逐筆呼叫完整通報 Python 查詢。
- A 級且五個指定欄位依序為 true、true、false、false、false 時，將通報號與新增日期寫入等候結案庫，並從主資料表移除；`Sufficient Data for Fault Analysis` 不參與判斷。B 級或未符合者留在主資料表。
- 兩庫搬移使用 SQLite attached database transaction，確保單筆插入與刪除一起 commit 或 rollback。明細失敗時保留已完成 snapshot 和先前成功處理的結果，錯誤摘要標示部分進度。
- 預設模式不呼叫 AI；明確加入 `--check-analysis-readiness` 才對待處理通報逐筆啟用付費 AI。
