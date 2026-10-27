# AI-Ready 任務卡：自動查詢空氣軟管日期

## Metadata

- 任務：新增批次空氣軟管日期查詢與 Excel 續跑程式。
- 上層規格：`../feature-spec-air-hose-date-batch.md`。
- 上層 Epic：MMIS HTTP 定期檢修工單明細查詢。
- 上層 User Story：批次彙整軟管日期、網路錯誤後續跑。
- 分軌：後端。
- 前置任務（dependsOn）：無；重用的單筆 Reader 已在目前工作區提供，但尚未提交。
- 狀態：已驗收；使用者於 2026-10-27 確認來源 64 個「車組/車號」均出現在輸出活頁簿，並完成任務驗收。
- 風險等級：高，MMIS 網路查詢與本機檔案寫入。
- Agent owner：Codex。
- 人工核准者：使用者以 2026-10-27 明確實作要求核准目標行為；續跑實作細節由架構階段決定。

## 目標

新增 `python -m tools.mmis_development.auto_query_air_hose_dates`，逐筆查詢來源 Excel 中的工作單，把七欄結果寫入目標 Excel，並支援失敗重試及中斷續跑。

## 情境包（Context Pack）

- 相關檔案：見 [任務情境包](../context-pack-air-hose-date-batch.md)。
- 既有模式：直接呼叫 periodic inspection Reader；參照 `periodic_inspection/workbook.py` 的 Excel 驗證、query 重建與逐筆原子保存。
- 假設：來源目前有 64 筆；目標只有七欄表頭。每筆查詢依來源列展開量測資料。
- 未知事項：無。架構決策已記錄於 `../architecture-plan-air-hose-date-batch.md`。
- 允許變更的檔案：`periodic_inspection/air_hose_workbook.py`、`tools/mmis_development/auto_query_air_hose_dates.py`、`tests/test_air_hose_workbook.py`、`tests/test_architecture.py`、development README、project map、架構地圖、code-search guide、source inventory 與本 Epic 產出物。
- 不得觸碰：本次開始前已有的未提交變更、指定 Downloads 活頁簿、憑證、Recorder evidence、其他 domain、production CLI 與 MMIS 遠端資料。

## 需求

- 讀取來源工作簿的「最新檢修工單」工作表，驗證四個來源欄位。
- 依來源順序逐筆呼叫 `run_air_hose_dates(工作單)`。
- 每個查詢記錄輸出七欄，欄位順序與使用者指定相同。
- 一次查詢最多重試三次；重試建立新的 MMIS session。
- 查詢失敗耗盡重試後，保留未完成狀態並繼續處理其餘來源列。
- 每筆成功結果和完成狀態原子保存；下次執行略過完成列並重試未完成列。
- 零筆和不支援結果分別記錄完成狀態，不在可見輸出建立虛假的量測列。
- 檢查來源工作簿快照，拒絕將舊進度用於已變更的來源資料。
- 不新增 MMIS 寫入事件，不在日誌中輸出認證資料。

## 驗收標準

- 車組/車號、檢修級別、工作單與檢修日期值保持來源值；車型來自查詢；檢查項目和量測值來自每筆 record。
- 一個工作單有多筆 record 時，每筆都輸出一列，四個來源值重複填入。
- 連續三次查詢失敗後，該來源列未標記完成，程式仍查詢後續來源列，結束時回報失敗並非零退出。
- 重跑略過成功列，並查詢先前失敗列；成功零筆和不支援列不會重查。
- 故障或活頁簿儲存中斷不會產生部分工作單資料，原目標檔仍可讀取。
- 驗證均使用臨時活頁簿與 stub，不存取 Downloads 檔案或 MMIS 網路。

## 實作備註

- 依架構計畫使用目標活頁簿內的隱藏進度工作表；完成資料和 checkpoint 一次原子保存。
- 保持新 development wrapper 精簡，批次資料處理留在 `src/mmis_connector/periodic_inspection/`。
- 先確認目前工作區未提交變更，避免改動已存在的查詢實作。

## 驗證契約

- 單元測試：來源與輸出結構、七欄對應、零筆與不支援、重試、繼續處理、續跑、原子保存與來源變更。
- 整合測試：`python -m pytest tests/test_air_hose_workbook.py tests/test_periodic_inspection_workbook.py -q`。
- E2E 測試：核准後才以指定正式檔案執行，不能取代離線測試。
- 型別檢查：不適用，專案未設定獨立 type checker。
- Lint：不適用，專案未設定獨立 lint。
- Build：`python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development`。
- 螢幕截圖：不適用，沒有 UI。
- 安全性檢查：檢查 `ai/checklists/security-checklist.md`，確認固定路徑、唯讀 MMIS、無 secret 輸出、原子檔案更新。

## 完成證據

- 變更的檔案：`src/mmis_connector/periodic_inspection/air_hose_workbook.py`、`tools/mmis_development/auto_query_air_hose_dates.py`、`tests/test_air_hose_workbook.py`、`tests/test_architecture.py`、development README、專案地圖/架構地圖/code-search guide/source inventory，以及本 Epic 的 context pack、feature spec、architecture plan、task card、audit 與 verification report。
- 執行過的指令：批次及既有查詢測試 50 passed；全專案 `python -m pytest -q -o addopts= -ra` 為 522 passed、40 skipped；compileall 與 `git diff --check` 通過；正式批次命令完成 64 筆查詢。
- 測試輸出：正式輸出活頁簿含 826 筆量測資料；64/64 個來源列 checkpoint 完成，所有資料區塊與 checkpoint digest 驗證通過，unsupported、empty、failed 均為 0。詳細證據見 [驗證報告](../verification/air-hose-date-batch.md)。
- 螢幕截圖：不適用，沒有 UI。
- 已知限制：40 個現有測試因缺少 Recorder DOM/HAR fixture 而 skip；本次即時查詢未觸發網路失敗重試，該情境由離線測試覆蓋。通用 MMISClientError 最多重試三次，偶有確定性錯誤時可能增加唯讀請求。
- 後續任務：若新增車型或更改 Excel 欄位，另開任務更新映射及驗證。
