# 清查逾期工單架構

`src/mmis_connector/overdue_work_orders.py` 負責 HTTP app 切換、表格解析與分頁檢查。`tools/mmis_development/audit_overdue_work_orders.py` 負責執行入口、SQLite 快照與備註，保持開發工具依賴正式 component 的既有方向。資料形狀是八個來源字串欄位，加一個「備註」欄。

HAR 的 `changeapp` 事件使用 `ZZ_WO_OVERDUE`、焦點 `FavoriteApp_ZZ_WO_OVERDUE`，頁面 app id 是 `zz_wo_overdue`。分頁沿用 `parse_maximo_page_info` 與 Maximo `click` event。資料庫先完成遠端讀取，再於 `BEGIN IMMEDIATE` 交易中重建資料表。SQLite 回滾提供寫入失敗的保護；查詢失敗時不啟動資料庫交易。

安全範圍是本機唯讀 MMIS 查詢和本機資料庫寫入。若表格欄位或分頁結構變動，查詢會報錯，避免以不完整資料覆蓋舊快照。

建立快照後，工具按 `rowid` 讀取檢修級別為 `2A` 或 `3A` 的主工單。它重用同一個 `MMISSession`，逐筆呼叫 `CompletePeriodicInspectionWorkOrderStatusQuery`，保留狀態不在 `核簽中`、`工單結案` 的子工單。工具先在記憶體組成所有備註，再以一次 SQLite 交易寫入，最後讀出備註非空的完整資料列並列印 JSON 陣列。這個設計使任一子工單查詢失敗時不會留下部分備註；當次新快照與空白備註仍保留。

`--export-xlsx` 在備註交易完成後才執行。匯出函式使用 `_unclosed_ab_xlsx` 的 `configured_output_directory`、`read_snapshot`、`build_workbook`、`save_workbook`。資料是依 `rowid` 排序的 SQLite tuple，每個 tuple 都有九個 `DATABASE_FIELDS` 欄位；不從只含非空備註的 CLI 清單匯出。共用函式負責 `.env` 路徑、schema 與筆數驗證、微軟正黑體 12 點樣式、台北日期檔名，以及同名檔案的數字後綴。匯出失敗時命令回傳失敗，已完成的 SQLite 快照保留。

匯出入口先檢查每格文字不超過 32,767 字元，並將不合法控制字元錯誤改為不包含原文的訊息。這兩項檢查避免共用工作表函式靜默截短內容，或把原始欄位值列印到 CLI 錯誤中。

設計比較：在現有 CLI 內新增單一匯出函式，與另建 `_overdue_work_orders_xlsx.py` 模組都可重用共用函式。本功能只有一個呼叫者，選擇前者以減少一層跳轉；不修改共用 XLSX 模組，避免影響其他匯出指令。

逾期 XLSX 使用九欄欄名對應的固定欄寬。匯出前在記憶體依 `檢修級別`、`逾期天數`、`車組(輛)` 的文字值升冪排序，SQLite 的 `rowid` 順序不變。共用 `build_workbook` 的 `row_height` 會同時設定標題列，並依多行備註放大資料列；逾期匯出因此在建立工作表後，將標題列高設為 16，所有資料列高設為 15.5，不修改共用函式。
