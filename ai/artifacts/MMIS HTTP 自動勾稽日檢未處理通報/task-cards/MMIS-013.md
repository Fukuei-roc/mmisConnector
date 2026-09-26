# AI-Ready 任務卡

## Metadata

- 任務：建立自動勾稽 SQLite 可恢復狀態層
- 上層規格：`ai/artifacts/MMIS HTTP 自動勾稽日檢未處理通報/feature-spec.md`
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：建立批次資料與中斷續跑
- 分軌：後端
- 前置任務（dependsOn）：`MMIS-001`、`MMIS-002`
- 狀態：完成
- 風險等級：中
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-24）

## 目標

提供無網路依賴的 SQLite store，完整支援新批次清除、未完成批次續跑、來源匯入、逐筆狀態落盤與摘要。

## 情境包（Context Pack）

- 相關檔案：新 `src/mmis_connector/auto_link_store.py`、新 `tests/test_auto_link_store.py`、`.gitignore`。
- 既有模式：Python 3.11、標準函式庫優先、pytest、stdout 不由 store 輸出。
- 假設：預設 DB 位於 `data/auto_link_unprocessed_fault_notices.sqlite3`。
- 未知事項：無阻擋事項。
- 允許變更的檔案：上述三個檔案與本卡看板資料。
- 不得觸碰：MMIS query/linker、CLI、憑證、其他功能。

## 需求

- 依架構計畫建立固定 schema、參數化 SQL、foreign keys 與 transaction。
- 完成批次時清除舊資料並建立新 run；running 批次則返回續跑資訊。
- 無損保存 17 個來源欄位與 JSON；維護核心欄位、結果欄位及唯一鍵。
- 狀態更新逐筆 commit；提供可處理列、摘要與批次完成 API。
- 將 runtime SQLite 路徑加入 Git ignore。

## 驗收標準

- tmp_path 中可建立及重開 DB。
- 已完成 run 會在下一輪開始時被 transaction 清除；running run 不清除。
- 同一 run 重複通報號被拒絕且不產生部分匯入。
- 另一連線可立即讀到已 commit 的逐列狀態。
- `linking` 恢復為不可重試的 `link_error`。

## 實作備註

- 不引入 ORM 或第三方依賴。
- SQL 欄名固定定義，不由 MMIS header 動態生成。
- 所有 timestamp 使用帶 timezone 的 ISO 8601 UTC。

## 驗證契約

- 單元測試：schema、建立／清除／續跑、匯入原子性、唯一鍵、狀態 commit、摘要、`linking` 恢復。
- 整合測試：以兩個 SQLite connection 驗證落盤可見性。
- E2E 測試：不適用。
- 型別檢查：專案未配置。
- Lint：專案未配置；執行 `git diff --check`。
- Build：`python -m compileall -q src tests`。
- 螢幕截圖：不適用。
- 安全性檢查：檢查參數化 SQL、DB ignore、未儲存 secret。

## 完成證據

- 變更的檔案：`.gitignore`、`src/mmis_connector/auto_link_store.py`、`tests/test_auto_link_store.py`、本 Epic 治理 artifacts。
- 執行過的指令：targeted pytest、compileall、pip check、diff check。
- 測試輸出：9 passed；語法、依賴與 diff 檢查通過。
- 螢幕截圖：不適用。
- 已知限制：SQLite 含內部資料，需以本機檔案權限保護；跨 MMIS/SQLite 原子性由下一卡的 fail-closed 狀態機處理。
- 後續任務：`MMIS-014`。
