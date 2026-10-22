# AI-Ready 任務卡

## Metadata

- 任務：MMIS-063 將結果欄改名並區分查無日檢工單。
- 上層規格：`../feature-spec.md` 的「執行結果欄位修正」。
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報。
- 上層 User Story：使用者可從資料庫直接辨識已查詢但找不到工單的通報。
- 分軌：後端。
- 前置任務（dependsOn）：MMIS-062，已完成。
- 狀態：完成。使用者於本次對話明確要求修改、實作與驗證。
- 風險等級：高。涉及現有 SQLite 欄位遷移與結果表同步觸發器。
- Agent owner：Codex。
- 人工核准者：本次對話使用者。

## 目標

`fault_notices` 實體表及 `自動勾稽結果` 檢視表的末欄改為「執行結果」；`no_matching_work_order` 顯示「未找到對應日檢工單」。

## 情境包

- 相關檔案：`src/mmis_connector/auto_link/store.py`、`tests/test_auto_link_store.py`、`README.md`、本 Epic 的規格與驗證文件。
- 既有模式：`auto_link_state.processing_status` 是唯一處理狀態；`RESULT_PROJECTION` 生成 11 欄結果表，SQLite triggers 與內部狀態同交易同步；現有資料庫有 14 筆 `no_matching_work_order`。
- 假設：只新增指定的狀態文字，其餘原有「是／否／未執行」對照不變。內部英文狀態碼及 CLI 摘要鍵不改。
- 未知事項：無。
- 允許變更的檔案：上述程式、測試、README、本 Epic 的規格／任務／驗證文件，以及備份後的預設 SQLite 資料庫。
- 不得觸碰：MMIS 遠端流程、憑證、`.gitignore` 既有修改及無關功能。
- 情境預算備註：已讀專案地圖、store、相關測試與現有 SQLite schema／狀態計數；未讀敏感通報內容或無關功能。

## 資料契約與驗收標準

- `fault_notices` 仍為正好 11 欄的實體表，前十欄不變，末欄為「執行結果」。`自動勾稽結果` 檢視表同名同序。
- `linked` 顯示「是」；`linking` 與 `link_error` 顯示「否」；`no_matching_work_order` 顯示「未找到對應日檢工單」；其他狀態維持「未執行」。
- 既有資料庫在單一 SQLite 交易內改欄名、更新舊結果值及同步觸發器。失敗時保留舊 schema 與資料。
- 既有 14 筆查無工單資料在遷移後均顯示新文字；內部狀態、批次識別、通報數、工單號與續跑規則不變。
- 新建資料庫、再次開啟與後續狀態更新均使用新欄名和新文字。

## 驗證契約

- 暫存 SQLite 測試新建、舊 schema 遷移、各狀態投影、同交易同步及重開不重寫。
- 對正式 SQLite 先以 SQLite backup API 備份；在複本驗證後才本機遷移，並用全新唯讀連線核對欄位、14 筆結果與完整性。
- 執行相關與全套 pytest、`python -m compileall -q src tests`、`git diff --check`。
- 不執行會修改 MMIS 的正式批次；無 UI 螢幕截圖。

## 完成證據

- 見 `../verification/MMIS-063.md`；現有 14 筆資料均已顯示「未找到對應日檢工單」。
