# AI-Ready 任務卡

## Metadata

- 任務：MMIS-061 提供自動勾稽結果的正體中文 SQLite 檢視表。
- 上層規格：`../feature-spec.md` 的「結果檢視」補充規格。
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報。
- 上層 User Story：使用者可直接查閱本輪通報與已確認的勾稽結果。
- 分軌：後端。
- 前置任務（dependsOn）：MMIS-013、MMIS-014、MMIS-015，均已完成。
- 狀態：完成。使用者於 2026-10-22 核准分析建議並要求實作。
- 風險等級：高。資料庫結構與 MMIS 遠端勾稽結果的呈現。
- Agent owner：Codex。
- 人工核准者：本次對話使用者。

## 目標

在現有 SQLite 中提供欄名與順序固定的 11 欄唯讀檢視表，讓使用者直接查閱本輪來源資料及勾稽結果。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/auto_link/store.py`、`tests/test_auto_link_store.py`、`tests/test_auto_link_unprocessed_fault_notices.py`、`README.md`。
- 既有模式：`runs` 與 `fault_notices` 保存來源及續跑狀態；`created_at` 為來源查詢完成後匯入時的 UTC 時間；`processing_status` 區分已選工單、勾稽中、成功與錯誤。
- 假設：所有來源列同一批匯入，共用同一筆匯入時間；舊資料可用原 `created_at` 換算台北時間。
- 未知事項：無產品決策待釐清。
- 允許變更的檔案：上述程式、測試、README 與本 Epic 的規格、任務及驗證文件。
- 不得觸碰：正式 SQLite 內容、MMIS 網路流程、`.gitignore` 的既有修改、憑證及錄製證據。
- 情境預算備註：已讀專案／架構地圖、精確相關程式與測試、原功能規格及 MMIS 知識庫；未讀無關功能或敏感通報資料。

## 需求

- 新增唯讀檢視表 `自動勾稽結果`，依序提供「查詢時間、車次、車組/車號、發生日期、事故等級、ATP故障、故障現象、狀態、通報號、已關聯的工單、關聯執行成功」。
- 查詢時間為來源查詢後匯入時間，從 UTC 換算成附 `+08:00` 的台北時間；續跑不變。
- 已關聯的工單只在 `linked` 顯示工單號；`linked` 為「是」，`linking` 或 `link_error` 為「否」，其餘為「未執行」。
- 保留原表、CLI 摘要與遠端勾稽行為。既有 SQLite 開啟後也能取得檢視表。

## 驗收標準

- `PRAGMA table_info('自動勾稽結果')` 僅有上述 11 欄，順序相同且欄名為正體中文。
- 暫存 SQLite 實際查詢可核對台北時間與 UTC 原值，以及成功、錯誤、未執行各狀態。
- 既有資料庫結構可直接開啟；中斷續跑與完成後清除規則不變。

## 驗證契約

- 單元測試：11 欄契約、時間換算、來源值、狀態對照、舊表相容。
- 整合測試：既有自動勾稽 fake runner 測試。
- E2E 測試：不執行正式命令，因會寫入 MMIS；僅以暫存 SQLite 讀回檢視表。
- 型別檢查：不適用，專案沒有型別檢查關卡。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tests`。
- 螢幕截圖：不適用，無 UI。
- 安全性檢查：檢查唯讀檢視表、不加入敏感資料或改變遠端寫入策略。

## 完成證據

- 實作與驗證記錄於 `../verification/MMIS-061.md`。
