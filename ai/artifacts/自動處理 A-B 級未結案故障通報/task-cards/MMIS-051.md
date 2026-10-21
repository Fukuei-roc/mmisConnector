# AI-Ready 任務卡

- 任務：MMIS-051 同步成功後填寫故障分析
- 上層 Epic：自動處理 A-B 級未結案故障通報
- User Story：將具備分析資料且尚未完成分析的通報寫入 MMIS
- 狀態：已完成；人工核准：使用者 2026-10-21 明確要求實作並允許修改 MMIS 資料
- 風險：高（遠端 MMIS 寫入、付費 AI、本機 SQLite 回填）
- 前置任務：MMIS-049（完成）

## 情境包

- 相關檔案：`auto_process_unclosed_ab_fault_notices.py`、`query_fault_notice_full_detail.py`、`fault_notices/reader.py`、`events.py`、`parser.py`、相關測試及 2026-10-21 錄製。
- 既有模式：同步完成後讀 SQLite；以通報號唯一定位；Maximo event 走現有 session，寫入後重新查詢確認；失敗不自動重送保存事件。
- 允許變更：本任務涉及的 Development Tool、fault notice 寫入元件、parser、測試、Production Source Inventory 及本 Epic 治理產出物。
- 不得觸碰：正式 SQLite、錄製證據、憑證、無關 Production CLI 與範本。
- 驗證：錄製事件及 DOM 對照、mock HTTP 與暫存 SQLite 測試、完整相關 pytest、compileall。
- 情境預算：只讀相關同步、查詢、事件、解析器與測試；跳過無關 UI 和工單模組。

## 契約與驗收

- 只有完整同步成功後才從資料庫挑選 `Sufficient Data for Fault Analysis = 1` 且 `Fault Analysis Completed = 0` 的通報號。
- 每筆以既有完整通報 `--ai-analysis` 取得三個非空欄位，核對通報號，填入 MMIS 故障分析頁簽並觸發「儲存故障通報管理」。
- 寫入前核對唯一通報與目前欄位，保存後重新查詢三欄一致，才將 SQLite 備註改為「填寫故障分析完成」。
- 若 MMIS 現有三欄有部分非空值，保留既有文字，只用 AI 結果補空欄，避免覆寫人工內容。
- 不更新 SQLite 的 `Fault Analysis Completed`；任何寫入結果不明時，不重送保存，保留該筆備註空白並回報錯誤。
- 無符合資料時不呼叫 AI 或 MMIS 寫入。原有 XLSX 匯出保留既有語意。

## 非目標與風險控制

- 不修改 MMIS ATP 故障分析、事故現象或處理概況。
- 不更改資料庫 schema。SQLite 更新以通報號、兩個狀態欄位與備註空白為條件。
- 遠端保存與本機備註無法共用交易；保存成功但本機寫入失敗時，需人工確認或下次重新查詢，不自動重送未知結果。

## 驗證證據

- `python -m pytest -q`：全部通過，既有環境條件測試依原標記跳過。
- `python -m compileall -q src/mmis_connector tools/mmis_development`、`git diff --check`：通過。
- 原始錄製 HAR 顯示三次 setvalue，其中最後一次與 `toolactions_SAVE-tbb` click 同 POST，回應包含 `BMXAA4205I`；程式事件順序相符。
- `python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices`：實際執行成功，載入 5 筆、故障分析候選 1 筆、寫入 1 筆。
- 讀回 `1151019-10` 的 MMIS 故障分析三欄均非空；SQLite 該筆為 `(Sufficient=1, Completed=0, 備註=填寫故障分析完成)`。
- 未改畫面或視覺元件，無 UI 截圖要求。殘留風險為 MMIS 與 SQLite 之間無跨系統交易；保存結果不明時停下且不自動重送。
