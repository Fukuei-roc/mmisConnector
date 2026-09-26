# 功能規格書

## Metadata

- 功能：自動勾稽日檢未處理通報（Auto-Link Unprocessed Fault Notices to Daily Inspection Work Orders）
- 建議 CLI：`auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders`
- 負責人：待指定
- 狀態：人工已核准（2026-09-24）
- 風險等級：高（MMIS 遠端寫入、SQLite 狀態資料、批次操作）

## 問題

內部使用者目前必須先查詢「本段未處理通報」，再逐筆以車組／車號及發生日期尋找後續的動力車日檢（1A）工單，最後以工作單號與故障通報號執行勾稽。流程耗時且容易漏件，也缺少可在中斷後安全續跑的持久狀態。

## 使用者

- 已獲授權操作 MMIS 故障通報及動力車日檢（1A）工單的內部使用者。

## 目標

- 以單一 CLI 自動完成未處理通報查詢、SQLite 儲存、1A 工單查詢、故障通報勾稽及逐筆結果紀錄。
- 每筆使用「車組/車號」與「發生日期」查詢日檢工單；日期條件為 `>發生日期`。
- 查無對應工單視為正常業務結果並跳過勾稽。
- 每筆狀態立即提交至 SQLite，使非預期中斷後可安全續跑。
- 已完成一輪後再次啟動時，清除前一輪資料並建立新一輪；若前一輪尚未完成，則續跑未完成資料。

## 非目標

- 不新增 GUI、Web UI、Excel 匯入或 Excel 匯出。
- 不改變三個既有查詢／勾稽命令的公開行為。
- 不使用 Playwright 或瀏覽器 fallback。
- 不自動重送任何結果不明的 MMIS 勾稽寫入。
- 不替使用者排程執行，也不管理 Windows 工作排程器。
- 不勾稽無法唯一、安全決定目標工單的通報。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 建立批次資料 | 身為內部使用者，我想取得本段未處理通報並存入 SQLite，以便追蹤整批進度 | 所有查詢列完整落盤；保留來源欄位及批次識別 |
| 尋找日檢工單 | 身為內部使用者，我想依車組／車號及發生日期尋找後續 1A 工單，以便知道可勾稽的目標 | 零筆、唯一命中及多筆命中皆有明確狀態；零筆不算系統失敗 |
| 自動勾稽 | 身為內部使用者，我想把故障通報勾稽到安全決定的 1A 工單，以便省去逐筆操作 | 僅以工作單號及通報號執行；成功需沿用既有領域驗證；結果不明不得自動重送 |
| 中斷續跑 | 身為內部使用者，我想在程式中斷後繼續未完成工作，以便不重複已確認的遠端寫入 | 每筆立即提交；重新啟動未完成批次時，只處理可安全重試的列 |
| 開始新一輪 | 身為內部使用者，我想在前一輪完成後重新執行，以便只保留本次未處理通報 | 啟動新批次前清除上一輪 SQLite 業務資料，再載入最新查詢結果 |

## 使用者旅程

```text
身為已授權的 MMIS 內部使用者
我執行一個批次 CLI
系統登入一次並重用同一 MMIS session
系統若發現未完成批次則續跑，否則清除上一輪資料並建立新批次
系統查詢本段未處理通報並逐筆持久化
系統逐筆查找發生日期之後的 1A 工單
系統記錄工作單號或「查詢不到對應工單」
系統只對安全決定的工作單執行一次勾稽並立即記錄結果
最後輸出本輪摘要 JSON
```

## 功能需求

- WHEN CLI 啟動，THE SYSTEM SHALL 從既有 `.env` 載入 MMIS 設定，建立一個 `MMISSession`，並在整批流程中重用該 session。
- WHEN SQLite 不存在，THE SYSTEM SHALL 建立資料庫、批次 metadata 及故障通報資料表。
- WHEN SQLite 存在且最近批次為完成狀態，THE SYSTEM SHALL 在取得新資料前，以 transaction 清除上一輪業務資料並建立新批次。
- WHEN SQLite 存在且最近批次尚未完成，THE SYSTEM SHALL 視為中斷續跑，不重新清除或重新匯入來源列。
- WHEN 建立新批次，THE SYSTEM SHALL 呼叫既有 `UnprocessedFaultNoticeQuery`，並將每筆來源記錄完整存入 SQLite。
- WHEN 讀取每筆來源記錄，THE SYSTEM SHALL 從 `車組/車號`、`發生日期`、`通報號` 取得查詢與勾稽輸入；本流程中的「故障通報號」對應來源欄位 `通報號`。
- WHEN 將來源 `車組/車號` 用於日檢工單查詢，THE SYSTEM SHALL 先移除所有非數字字元；若所得數字為首位 `9` 的四位數 900 型單車車號，SHALL 再移除最後一位車廂碼。例如 `EP9393` 查詢 `939`、`EMU946` 查詢 `946`、`EMC722` 查詢 `722`。
- WHEN 正規化後沒有任何數字，THE SYSTEM SHALL 將該列標記為 `invalid_source_data`，不得呼叫日檢工單查詢或勾稽。
- WHEN 發生日期合法，THE SYSTEM SHALL 正規化為 `YYYY/MM/DD` 並以 `>YYYY/MM/DD` 呼叫既有 `DailyInspectionWorkOrderQuery`。
- WHEN 缺少或無法解析車組／車號、發生日期或通報號，THE SYSTEM SHALL 將該列標記為 `invalid_source_data`、記錄非敏感錯誤，並繼續下一列。
- WHEN 日檢工單查詢為零筆，THE SYSTEM SHALL 將 `日檢工單號` 寫為空值、狀態標記為 `no_matching_work_order`、結果訊息記錄「查詢不到對應工單」，並跳過勾稽。
- WHEN 能安全決定一筆工單，THE SYSTEM SHALL 將其 `工作單` 寫入 `日檢工單號`，再以該工作單號與來源 `通報號` 呼叫既有 `DailyInspectionWorkOrderFaultNoticeLinker`。
- WHEN 勾稽成功且既有領域驗證通過，THE SYSTEM SHALL 將該列標記為 `linked`。
- WHEN 查詢發生可安全重試的錯誤，THE SYSTEM SHALL 記錄 `query_failed` 並繼續下一列；下次續跑可再嘗試該列。
- WHEN 勾稽發生任何錯誤（包含寫入前失敗、結果不明或驗證失敗），THE SYSTEM SHALL 記錄 `link_error` 與非敏感錯誤摘要，且本次及後續續跑都不得自動重送該列。
- WHEN 任一列狀態改變，THE SYSTEM SHALL 使用獨立 SQLite transaction 立即提交該列的工作單號、狀態、結果訊息、嘗試次數及時間戳。
- WHEN 所有列都到達終止狀態且沒有 `link_error`，THE SYSTEM SHALL 將批次標記為完成；若存在 `link_error`，批次維持未完成以保留資料並阻止新批次自動重送相同通報。
- WHEN 另一個同資料庫的批次程序正在執行，THE SYSTEM SHALL 在任何 MMIS 操作前安全失敗，不得並行處理相同資料列。
- WHEN 程式處理列，THE SYSTEM SHALL 使用穩定主鍵防止同一批次內重複匯入同一通報號。

## 工單選擇規則（待人工核准）

推薦採安全規則：

- 零筆：記錄「查詢不到對應工單」，不勾稽。
- 一筆：使用該筆工作單。
- 多筆：選擇「檢修日期最早且晚於發生日期」的一筆；若最早日期仍有多筆不同工作單，標記 `ambiguous_work_order` 並停止該列，不做遠端寫入。

不得單純依 MMIS 未保證的畫面排序取第一筆。

## 畫面

- 無 UI；本功能為 CLI 與 SQLite 資料流程，不需要 mockup 關卡。

## 資料與 API

- CLI 輸入：無必要位置參數；資料庫路徑採專案內固定預設值，實際路徑在架構規劃階段定案。
- CLI 輸出：穩定 JSON 摘要，至少包含 `success`、`run_id`、`resumed`、`total`、`linked`、`no_matching_work_order`、`failed`、`manual_review_required`、`database_path`。
- SQLite `runs`：`run_id`、`status`、`started_at`、`completed_at`、來源查詢名稱、各狀態計數。
- SQLite `fault_notices`：內部 id、`run_id`、17 個來源欄位（採穩定英文欄名）、完整來源 JSON、`daily_inspection_work_order_no`（顯示名稱「日檢工單號」）、`processing_status`、`result_message`、`attempt_count`、`created_at`、`updated_at`。
- 唯一鍵：同一 `run_id` 下的來源 `通報號` 唯一。
- 日期驗證：接受來源可正規化的日期，送往既有查詢前統一為 `>YYYY/MM/DD`。
- 錯誤：區分來源錯誤、正常零筆、查詢失敗、多筆歧義、勾稽錯誤及已確認成功；任何勾稽錯誤都是不可自動重試的終止狀態。
- SQLite 僅使用 Python 標準函式庫 `sqlite3`，不新增 ORM 依賴。

## 安全性與隱私

- 身分驗證：沿用 `MMISConfig.from_env()` 與 `MMISSession`；不得將帳密寫入 SQLite 或 log。
- 權限：程式不提升權限；執行者必須已獲 MMIS 勾稽權限。
- 敏感資料：SQLite 含內部故障通報資料，不得提交 Git；資料庫檔案應加入忽略規則並限制在明確路徑。
- 遠端寫入：勾稽 POST 禁止 transport retry；只在既有 linker 完成精確工單驗證後寫入，並以故障通報號出現在回應表格中確認成功。
- 結果不明：不得自動重送，必須保留人工確認狀態。
- 日誌：不得輸出 cookie、CSRF token、session id、帳密或整筆來源內容。

## 驗收標準

- 新 CLI 可在一次登入及同一 session 中編排三個既有能力。
- 新批次將所有本段未處理通報完整存入 SQLite，來源筆數與查詢結果一致。
- 每筆以正規化後的數字車號與 `>發生日期` 查詢 1A 工單；900 型四位單車車號需去除末位車廂碼。
- 零筆結果寫入「查詢不到對應工單」語意並跳過勾稽。
- 唯一、安全決定工單時，SQLite `日檢工單號` 與既有 linker 輸入一致。
- 每列結果在處理後立即可由另一個 SQLite 連線讀取。
- 模擬在任意列中斷後重新啟動，不重做 `linked`、`no_matching_work_order` 或 `link_error` 列，只繼續尚未進入勾稽階段或僅查詢失敗的列。
- 已完成批次再次啟動時，舊業務資料被清除並由最新查詢結果取代。
- 多筆工單依核准規則處理，不會因未定義排序而誤勾稽。
- 任一勾稽錯誤都不自動重送，SQLite 保留錯誤摘要且摘要顯示需人工確認。
- 既有完整 pytest 套件持續通過。

## 驗證計畫

- 單元測試：SQLite schema／transaction、日期與來源欄位轉換、狀態機、工單選擇、摘要計數、完成批次清除、未完成批次續跑。
- 整合測試：以 fake `MMISSession`／query／linker 驗證單一 session 編排，涵蓋零筆、一筆、多筆、單列查詢失敗、勾稽成功、結果不明與程序中斷。
- 回歸：`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`、`git diff --check`。
- E2E：因會批次變更 MMIS 資料，須另取得指定資料範圍的一次性人工授權後才能執行；不得以未核准的 live 資料試跑。
- 視覺：不適用。
- 手動：以 SQLite 查詢核對來源筆數、逐筆狀態、工單號、續跑結果及摘要計數。

## 情境包

- 任務：新增「自動勾稽日檢未處理通報」批次編排程式。
- 目標：重用既有三個 HTTP-only MMIS 功能，以 SQLite 實作可恢復且不重複遠端寫入的批次流程。
- 相關檔案：`src/mmis_connector/query_unprocessed_fault_notices.py`、`query_daily_inspection_work_orders_by_vehicle_and_date.py`、`link_fault_notice_to_daily_inspection_work_order_by_number.py`、`cli.py`、`auth.py`、對應 tests 與本 Epic artifacts。
- 既有模式：一個 `requests.Session`、動態 Maximo table schema、stdout JSON、寫入 POST 不重試、領域資料驗證成功。
- 假設：需求第 2 步重複的「發生日期」應為「車組/車號」與「發生日期」；第 3 步的 `>發生日期` 是日期條件；來源 `通報號` 即 linker 所需故障通報號。
- 未知事項：多筆工單選擇規則尚待核准；完成／中斷時的重新啟動語意尚待核准；SQLite 最終路徑待架構規劃。
- 允許變更的檔案：待規格核准及任務卡建立後列出。
- 不得觸碰：既有三個命令契約、憑證與錄製 HAR、UI／瀏覽器自動化。
- 驗證指令：見「驗證計畫」。
- 風險等級：高。
- 情境預算備註：已讀專案／架構／搜尋地圖、流程與 DoR、三個核心模組、CLI、精確相關測試、既有功能規格及 MMIS 知識庫；未讀無關功能與完整錄製資料，因現有證據已足以形成產品規格。

## 人工核准紀錄

- 2026-09-24：確認第 2 步欄位為「車組/車號」與「發生日期」，第 3 步使用「車組/車號」與 `>發生日期` 查詢。
- 2026-09-24：核准多筆工單採「檢修日期最早」的一筆；若最早日期仍有多筆不同工單則拒絕勾稽。
- 2026-09-24：核准未完成批次自動續跑，已完成批次才清除資料並開始新一輪。
- 2026-09-24：要求任何勾稽錯誤只寫入 SQLite，不得自動重跑。
