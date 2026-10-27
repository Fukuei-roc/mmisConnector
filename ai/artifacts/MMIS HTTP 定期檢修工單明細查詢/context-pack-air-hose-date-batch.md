# 任務情境包：自動查詢空氣軟管日期

任務：新增批次查詢程式，逐筆讀取配屬車號總表的工作單，查詢附表一空氣軟管日期資料，並寫入指定 Excel。

目標：將來源的車組/車號、檢修級別、工作單、檢修日期，與查詢的車型、檢查項目、量測值合併成目標活頁簿資料列。網路查詢失敗時重試，執行中斷後可從未完成的來源工作單繼續。

相關檔案：

- `src/mmis_connector/periodic_inspection/reader.py` 的 `PeriodicInspectionWorkOrderDetailReader.run_air_hose_dates()`。此方法目前在工作區的未提交變更中。
- `src/mmis_connector/periodic_inspection/workbook.py` 的來源活頁簿驗證、逐列查詢、重試與原子儲存模式。
- `src/mmis_connector/periodic_inspection/air_hose_workbook.py` 的多筆量測回填與隱藏進度紀錄。
- `tools/mmis_development/query_periodic_inspection_work_order_air_hose_date.py` 的 development tool 與 JSON 輸出模式。此檔目前是未追蹤的工作區變更。
- `tools/mmis_development/fill_latest_periodic_inspection_work_orders.py` 與對應測試。
- `tests/test_periodic_inspection_workbook.py`。
- `tools/mmis_development/README.md` 與 `ai/context/project-map.md`。
- 使用者指定的兩個 Excel 活頁簿。已讀取表頭、工作表名稱與來源筆數，沒有修改活頁簿。

既有模式：

- Development tool 直接呼叫 `src/mmis_connector/` 的 domain component，不以 subprocess 呼叫其他 tool，也不解析另一個 CLI 的 JSON。
- `PeriodicInspectionWorkOrderDetailReader.run_air_hose_dates()` 回傳車型與 `records`，每筆只有「檢查項目」及「量測值」。
- `periodic_inspection/workbook.py` 以 openpyxl 驗證工作表和表頭，查詢失敗後重建 query/session，成功一筆即以同目錄暫存檔和 `os.replace` 原子儲存。
- 專案以唯讀 Maximo event 查詢，不對 Maximo 寫入事件啟用自動重試。

已觀察的輸入與輸出：

- 來源 `配屬車號總表.xlsx` 的工作表是 `最新檢修工單`，A 至 D 欄依序為「車組/車號」、「檢修級別」、「工作單」、「檢修日期」。目前有 64 筆完整資料，沒有空白資料列或重複工作單。
- 目標 `空氣軟管日期.xlsx` 的工作表是 `空氣軟管日期`，A 至 G 欄依序為「車組/車號」、「車型」、「檢修級別」、「工作單」、「檢修日期」、「檢查項目」、「量測值」。目前只有表頭。
- 每筆來源工作單會對應零筆或多筆輸出資料。每筆量測資料重複寫入四個來源欄位，並填入查詢車型、檢查項目與量測值。

假設與待核對決策：

- 無參數執行，使用使用者指定的固定檔案路徑。
- 一次查詢失敗最多嘗試三次；每次失敗後重新建立 MMIS session。三次失敗後保留該工作單為未完成，記錄錯誤並繼續查下一筆；最後以非零結束狀態回報未完成工作單。
- 續跑狀態與每筆工作單結果在同一次原子活頁簿儲存中提交。使用目標活頁簿的隱藏進度工作表；既有可見資料若沒有可驗證的進度表，程式拒絕覆寫。
- 支援車型回傳的量測列寫入可見工作表；不支援車型或有效零筆結果不產生量測列，但應記錄為已完成並在執行摘要中標示，避免每次續跑都重查。
- 若來源工作簿內容在續跑前改變，應檢查來源快照並停止，避免把舊進度套用到新資料。
- 查詢模組與其單筆功能相關變更目前在工作區尚未提交。本任務預期重用它們，不負責重寫或回復。

未知事項：700 型目前的查詢證據尚未由本任務驗證；沿用單筆 Reader 的既有映射與測試。

允許變更的檔案：

- 新增 `src/mmis_connector/periodic_inspection/air_hose_batch.py` 或架構審查選定的同領域 module。
- 新增 `tools/mmis_development/auto_query_air_hose_dates.py`。
- 新增對應的 batch module 測試；必要時更新 `tests/test_architecture.py`。
- 更新 `tools/mmis_development/README.md`、`ai/context/project-map.md`。
- 更新 `ai/context/architecture-map.md`、`ai/context/code-search-guide.md` 及 `docs/development/production-source-inventory.md`。
- 新增本目標的規格、任務卡、架構與驗證產出物。

不得觸碰：

- 使用者指定的 Downloads 活頁簿，除非明確進入實際執行階段並依使用者核准執行。
- `.env`、憑證、token、Recorder 原始 evidence、其他 MMIS domain、production CLI routes 與 MMIS 遠端資料。
- 本次任務開始前已存在的未提交變更。

驗證指令：

- `python -m pytest tests/test_periodic_inspection_air_hose_batch.py -q`。
- `python -m pytest tests/test_periodic_inspection_workbook.py tests/test_architecture.py -q`。
- `python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development`。
- `git diff --check`。
- 以臨時測試活頁簿驗證重試、逐筆保存、續跑、零筆完成、來源變更保護與輸出欄位。不得以正式 Downloads 檔案或即時 MMIS 查詢取代離線驗證。

風險等級：高。功能使用 MMIS HTTPS session 並讀寫使用者檔案；MMIS 操作本身唯讀。需架構、安全與測試審查。

情境預算備註：讀取專案地圖、架構地圖、程式碼搜尋指南、共用流程、Definition of Ready/Done、security checklist、review gates、kanban 流程、feature spec/task card 範本、MMIS engineering knowledge、單筆空氣軟管 reader、development wrapper、週期檢修 workbook 批次模式及其測試。未檢視其他 domain、憑證或 Recorder 原始資料。指定 Downloads 活頁簿只讀取工作表名、表頭、資料列數及空白/重複檢查。
