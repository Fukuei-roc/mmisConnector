# MMIS Development Tools

## Purpose

這個資料夾存放為了 MMIS 功能開發、HTTP／Maximo event 驗證、debugging、受控 Live
測試與 reusable component 驗證而建立的可執行工具。它們不是 MMIS Connector 的正式
application workflow，也不會由正式 `mmis-connector` CLI dispatch。

## Architecture Rule

允許的依賴方向：

```text
development tools
       ↓
src/mmis_connector reusable components
       ↑
production applications
```

禁止：

```text
production application
       ↓
development tools
```

Development tool 必須保持薄：只處理 arguments、建立正式 component、執行與輸出 JSON。
Authentication、Maximo event、parser、validation 與 domain logic 只能存在於
`src/mmis_connector/`。

## Existing Tools

所有命令都從 repository root 執行：

| Tool | 用途 | 執行方式 |
|---|---|---|
| 查詢故障通報完整資料（最完整） | 輸入通報號；取得基本資料、ATP 標記、段檢修與 CA 查修工單、故障分析及 MMIS 原有 ATP 分析；指定 `--ai-analysis` 且為 ATP 故障時，另產生 ATP AI 分類建議。 | `python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14` |
| 查詢故障通報關聯的查修工單 | 輸入通報號；取得關聯的 CA 查修工單清單。 | `python -m tools.mmis_development.query_repair_work_orders_linked_to_fault_notice 1150930-09` |
| 查詢故障通報的故障分析 | 輸入通報號；取得事故現象、處理概況、故障原因、處理情形及改善對策。 | `python -m tools.mmis_development.query_fault_notice_analysis 1150828-12` |
| 查詢故障通報關聯的 ATP 故障分析 | 輸入已勾選 ATP 故障的通報號；取得故障要因、故障因子及故障項目。 | `python -m tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice 1150210-36` |
| 匯出 ATP 故障分析選項 | 自動遍歷故障要因、故障因子及故障項目，輸出完整階層樹。 | `python -m tools.mmis_development.export_atp_fault_analysis_options 1151012-36` |
| 查詢故障通報關聯的工單 | 輸入通報號；取得關聯的段檢修工單清單。 | `python -m tools.mmis_development.query_work_orders_linked_to_fault_notice 1150910-14` |
| 查詢未處理故障通報 | 無需輸入；取得本段未處理故障通報清單。 | `python -m tools.mmis_development.query_unprocessed_fault_notices` |
| 查詢未結案故障通報 | 無需輸入；取得新竹機務段 A、B 級未結案故障通報清單。 | `python -m tools.mmis_development.query_unclosed_fault_notices` |
| 自動處理 A/B 級未結案故障通報（開發階段） | 完整儲存待處理 A/B 級通報，逐筆查詢結案狀態檢查，將符合條件的 A 級通報移入等候結案資料庫；不修改 MMIS 資料。 | `python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices` |
| 自動處理 A/B 級未結案故障通報並匯出 XLSX | 先執行同一套 MMIS 查詢與 SQLite 全量同步，完整成功後再從本次更新的資料庫匯出 XLSX。 | `python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices --export-xlsx` |
| 查詢臨時檢修工單明細 | 輸入工作單號；取得工單基本資料、已勾稽故障通報、維修程序概況及試車報告。 | `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-41264` |
| 查詢日檢工單明細 | 輸入一個日檢工作單號；輸出基本資料、已勾稽故障通報、備註非空的檢修記錄、重要事項紀錄及檢修人員，完整欄位見 `recordings/README.md`。 | `python -m tools.mmis_development.query_daily_inspection_work_order_details 115-1A-71815` |
| 查詢定期檢修工單明細 | 輸入一個定期檢修工作單號；先查預設清單，確認零筆才切「所有記錄」重查。`success` 後依序直接輸出工作單、車組/車號、檢修級別、檢修日期、完工日期、工作單狀態六個第一層欄位。`維修程序概況` 取自檢修回報的紀事(備註)清單，含 count、records 及車組/車號、故障類別、故障類別說明、故障現象、故障原因、處置措施、材料編號(PA)、員工代號、人員姓名九欄。`檢修記錄` 只保留備註非空的列，含 count、records 及裝置名稱、檢修項目、回報結果、備註四欄。JSON 最後為動態資料頁簽的 `維修情形` 與 `維修情形(詳述)` 字串。 | `python -m tools.mmis_development.query_periodic_inspection_work_order_details 115-2A-69254-001` |
| 查詢最新定期檢修工單 | 輸入車組/車號；查詢檢修級別為 2A 或 3A、檢修單位為檢查室、工作單狀態為工單結案或簽核中的定期檢修工單。讀取所有結果頁後，依檢修日期選出最新的一筆，直接印出車組/車號、檢修級別、工作單、檢修日期四欄 JSON，不產生檔案。查無資料或結果不完整時回傳錯誤 JSON 及非零結束碼。 | `python -m tools.mmis_development.query_latest_periodic_inspection_work_order 813` |
| 依車號與日期查詢日檢工單 | 輸入車號與檢修日期條件；取得符合條件的日檢工單清單。 | `python -m tools.mmis_development.query_daily_inspection_work_orders_by_vehicle_and_date 717 '>2026/09/23'` |
| 依工作單號讀取明細 | 輸入日檢工作單號；取得該工單已勾稽的故障通報清單。 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number 115-1A-70048` |
| 依工作單號勾稽故障通報 | 輸入日檢工作單號與通報號；將通報勾稽至工單並確認結果。 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number_and_link_fault_notice 115-1A-71002 1150923-36` |

最後一項會修改 MMIS 資料。只能在明確核准的受控 Live 驗證或人工單筆操作中使用；若
結果不明，先人工確認，不得直接重送。

自動處理 A/B 級未結案故障通報先執行第一階段 snapshot。它在
`data/unclosed_ab_fault_notices.db` 建立 15 欄的 `unclosed_ab_fault_notices` 資料表，
以 `通報號` 為唯一鍵。僅寫入車次、車組/車號、發生日期、事故等級、ATP故障、故障現象、
狀態及通報號八個基本欄位；此時六個結案狀態檢查欄位及備註均為 SQLite `NULL`。
每次查詢完整成功後以 transaction 完整覆蓋舊資料，包含重新清空預留欄位；查詢或寫入
失敗則保留舊資料。

工具另在 `data/a_level_fault_notices_awaiting_closure.db` 保存「A-Level Fault Notices
Awaiting Closure」，資料表 `a_level_fault_notices_awaiting_closure` 只有 `通報號`（唯一鍵）
與 `新增日期`（台北時間、含時區的 ISO 日期時間）兩欄。此庫不隨主 snapshot 重建或清空。
  導入本次修復後，既有舊版等候結案資料庫會在下一次成功建立 snapshot 時清空一次，
  重新查詢全部 A/B 級未結案通報；之後的執行恢復保留等候結案名單並略過其中通報。
  這次重查與主資料庫 snapshot 在同一個 SQLite transaction 中完成，寫入失敗會回滾兩庫。
  首輪逐筆查詢完整通報的結案狀態時，不查詢額外的故障分析工單素材；完整通報查詢若發生錯誤，
  會立即重試一次，若仍失敗則等待 1 秒再試一次，三次均失敗才停止並回報失敗。
每次完整查詢後，已在等候結案庫的通報號會從主 snapshot 排除，也不再查詢完整明細。

snapshot 完成後，工具依本次來源順序逐筆直接呼叫既有完整通報 Python 查詢，將
`結案狀態檢查` 的六欄更新至主資料表。若事故等級為 `A`，且 `Fault Analysis Completed`
與 `All Depot Maintenance Work Orders Closed` 均為 `true`，而
`Depot Maintenance Work Orders Pending Approval`、`CA Repair Work Orders Not Closed`
及 `ATP Fault Analysis Incomplete` 均為 `false`，則在同一個 SQLite transaction 中將
通報號與新增日期寫入等候結案庫，並從主資料表移除。B 級通報不會進入等候結案庫。
`Sufficient Data for Fault Analysis` 不參與此搬移條件。

預設先查詢每筆通報的五項非 AI 結案檢查。只有 `Fault Analysis Completed` 為 `false` 的
通報，才再次呼叫完整明細查詢的 `--check-analysis-readiness` 模式，將回傳的
`Sufficient Data for Fault Analysis` 布林值寫入主資料庫的該欄；其餘通報的此欄維持
SQLite `NULL`。第二次查詢不改寫先前儲存的其他五項檢查結果。這項判斷會使用付費
OpenAI API，需設定 `OPENAI_API_KEY`，並將事故與相關工單素材送交 AI。若要沿用對每筆
待處理通報都檢查資料充分性的舊模式，可明確執行：

```powershell
python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices --check-analysis-readiness
```

兩種模式都不執行 `--ai-analysis`，也不修改 MMIS 系統資料。若資料充分性查詢因相關
工單證據不完整而無法判斷，正常模式會讓該筆欄位維持 `NULL`，繼續查後續通報，最後輸出
`partial_success`、未完成通報清單及非零 exit code，不將未知結果寫成 `false`。這類確定性的
資料錯誤不重試整筆完整明細；網路或其他明細錯誤仍依既有重試與失敗處理。已完成的
snapshot、先前成功搬移的通報及該筆已保存的五項非 AI 檢查結果都會保留。

`--export-xlsx` 每次都重新查詢 MMIS 並完成 SQLite 全量覆蓋及逐筆處理。
新快照的 `備註` 一律重置為 `NULL`；只有本次確認故障分析寫入成功後，才寫入
「填寫故障分析完成」。
完整成功後，它呼叫 `export_unclosed_ab_fault_notices_from_db`，從已提交的
`unclosed_ab_fault_notices` 資料表產生相同的九欄 Excel，並核對本次同步筆數。
若同步失敗或資料充分性仍有未完成項目，不會產生 XLSX。匯出失敗不回滾已成功同步的
SQLite，JSON 會區分同步與匯出結果並使用非零 exit code。

要從目前的 SQLite 資料獨立產生 Excel，從專案根目錄執行：

```powershell
python -m tools.mmis_development.export_unclosed_ab_fault_notices_from_db
```

此指令只讀取 `data/unclosed_ab_fault_notices.db`，不重新查詢 MMIS，也不重建資料庫。
`--export-xlsx` 使用此指令的輸出資料夾設定、檔名與 Excel 格式。Excel 只輸出八個基本欄位與
`備註`，省略六個英文結案狀態檢查欄位。所有列高固定為 15.5 pt，儲存格垂直靠上；
欄寬依序為 6.5、11.8、14.5、10.6、10.6、70、10.6、14.9、40。
資料依「事故等級」、「發生日期」、「車組/車號」逐級遞增排序；相同排序鍵保留
資料庫原順序。儲存格不依結案狀態填滿顏色。離線匯出依六個結案狀態欄位的完整組合，
將 `(NULL,1,0,0,0,0)`、`(NULL,1,0,1,0,0)`、`(NULL,1,1,0,0,0)` 的備註依序
設為「段修工單未處理完成」、「等候段修工單簽核中」、「可結案」。
`(NULL,0,0,1,0,0)`、`(0,0,0,1,0,0)` 與 `(0,0,0,0,0,0)` 的備註設為「未處理」。
其他組合保留 SQLite 原備註；只修改 Excel，不回寫 SQLite。
同步指令與獨立匯出指令使用相同的 Excel 格式。

請在專案 `.env` 設定 `UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR` 為既有的絕對輸出資料夾。
Excel 只有 `AB級未處理故障通報` 一張工作表，依前述規則匯出九欄；SQLite
`NULL` 為空白，布林 `1`／`0` 為 Excel `TRUE`／`FALSE`。所有儲存格使用微軟正黑體
12 pt，標題粗體置中、資料靠左；長文字啟用換行，列高固定為 15.5 pt。
檔名依台灣日期為 `AB級未處理故障通報_程式產生MMDD.xlsx`；同名時依序加 `_2`、
`_3`，不覆蓋既有檔案。若輸出資料夾不存在，程式會回報錯誤，不自行建立路徑。

查詢完整故障通報時，可依需求選擇是否產生 AI 故障分析：

```powershell
python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14
python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14 --ai-analysis
python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14 --check-analysis-readiness
python -m tools.mmis_development.query_fault_notice_full_detail 1151012-36 --ai-analysis
```

第一個指令只查詢 MMIS，不呼叫 OpenAI API。加上 `--ai-analysis` 後，工具會在原查詢完成後產生「故障原因」、「處理情形」、「改善對策」，並合併至 JSON 最後的「故障分析」物件；此模式會產生 API 費用，需先設定 `OPENAI_API_KEY`。設定方式見根目錄 `README.md`。

三種模式互斥：只提供通報號時，僅查詢完整資料；`--ai-analysis` 查詢並產生故障分析；`--check-analysis-readiness` 查詢後使用 AI 判斷相關檢修工單是否已有與本次事故現象有關的後續處理紀錄，不產生故障分析文章。後兩者不可同時指定，且均需設定 `OPENAI_API_KEY`。

`結案狀態檢查.Sufficient Data for Fault Analysis` 位於結案狀態檢查的第一欄：`true` 表示已有事故相關後續處理紀錄，`false` 表示沒有找到，`null` 表示未執行判斷。`true` 不代表故障已修妥，也不代表故障分析已完成。

當 `--ai-analysis` 已指定且「是ATP故障」為布林 `true`，工具也會使用相同的故障通報與工單素材，獨立產生 `ATP故障分析_AI建議`。即使 MMIS 原有三欄分類已完整、部分空白或全部空白，仍會執行 ATP AI 分類。`ATP故障分析` 保留 MMIS 原始填報值；AI 建議會依 `data/atp_fault_analysis_options.json` 的父子選項結構驗證，兩者可以不同。若無法產生合法分類，結果不會包含 AI 建議，而會提供 `ATP故障分析_AI建議錯誤`；原始通報、MMIS 分類及既有故障分析仍保留。此功能只提供建議，不會寫入 MMIS。

ATP 選項匯出工具屬於 Development / Diagnostic Tool。從專案根目錄執行：

```powershell
python -m tools.mmis_development.export_atp_fault_analysis_options 1151012-36
```

參數需為已勾選 ATP 故障、目前可查詢的通報號。工具使用 `.env` 建立有效 MMIS Session，僅以 HTTP 查詢與暫態 UI 選項事件讀取資料，不送出儲存或其他業務寫入事件。完整成功時會在專案的 `data/` 目錄原子更新 UTF-8 JSON `atp_fault_analysis_options.json`，內容包含三層選項樹、統計與狀態。若部分分支失敗，會將路徑與原因寫到同目錄的 `atp_fault_analysis_options.partial.json`，原有完整 JSON 不受影響；登入或初始查詢失敗則不更新檔案。重新執行完整成功時會更新原有 JSON。

## Future Development

```text
Recorder
  ↓
分析 HTTP / Maximo event
  ↓
建立 development tool
  ↓
離線測試
  ↓
受控 Live 驗證
  ↓
抽取／完善 reusable component
  ↓
整合 production application
```

Development tool 完成使命後：

- 仍有 debugging 或 reference 價值：留在此資料夾並維持測試與安全警示。
- 已無價值：刪除 wrapper，不影響正式 component。
- 具有共用價值的 implementation：永遠放在 `src/mmis_connector/`，不得留在 tool 中供
  production 反向 import。
