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
| 自動處理 A/B 級未結案故障通報（第一階段） | 查詢並整理 A/B 級未結案通報，只擷取 8 個基本欄位；不修改 MMIS 資料。 | `python -m tools.mmis_development.auto_process_unclosed_ab_fault_notices` |
| 查詢臨時檢修工單明細 | 輸入工作單號；取得工單基本資料、已勾稽故障通報、維修程序概況及試車報告。 | `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-41264` |
| 查詢日檢工單明細 | 輸入一個日檢工作單號；輸出基本資料、已勾稽故障通報、備註非空的檢修記錄、重要事項紀錄及檢修人員，完整欄位見 `recordings/README.md`。 | `python -m tools.mmis_development.query_daily_inspection_work_order_details 115-1A-71815` |
| 查詢定期檢修工單明細 | 輸入一個定期檢修工作單號；先查預設清單，確認零筆才切「所有記錄」重查。`success` 後依序直接輸出工作單、車組/車號、檢修級別、檢修日期、完工日期、工作單狀態六個第一層欄位。`維修程序概況` 取自檢修回報的紀事(備註)清單，含 count、records 及車組/車號、故障類別、故障類別說明、故障現象、故障原因、處置措施、材料編號(PA)、員工代號、人員姓名九欄。`檢修記錄` 只保留備註非空的列，含 count、records 及裝置名稱、檢修項目、回報結果、備註四欄。JSON 最後為動態資料頁簽的 `維修情形` 與 `維修情形(詳述)` 字串。 | `python -m tools.mmis_development.query_periodic_inspection_work_order_details 115-2A-69254-001` |
| 依車號與日期查詢日檢工單 | 輸入車號與檢修日期條件；取得符合條件的日檢工單清單。 | `python -m tools.mmis_development.query_daily_inspection_work_orders_by_vehicle_and_date 717 '>2026/09/23'` |
| 依工作單號讀取明細 | 輸入日檢工作單號；取得該工單已勾稽的故障通報清單。 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number 115-1A-70048` |
| 依工作單號勾稽故障通報 | 輸入日檢工作單號與通報號；將通報勾稽至工單並確認結果。 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number_and_link_fault_notice 115-1A-71002 1150923-36` |

最後一項會修改 MMIS 資料。只能在明確核准的受控 Live 驗證或人工單筆操作中使用；若
結果不明，先人工確認，不得直接重送。

自動處理 A/B 級未結案故障通報目前只執行第一階段。它在
`data/unclosed_ab_fault_notices.db` 建立 15 欄的 `unclosed_ab_fault_notices` 資料表，
以 `通報號` 為唯一鍵。僅寫入車次、車組/車號、發生日期、事故等級、ATP故障、故障現象、
狀態及通報號八個基本欄位；六個結案狀態檢查欄位及備註固定為 SQLite `NULL`。
每次查詢完整成功後以 transaction 完整覆蓋舊資料，包含重新清空預留欄位；查詢或寫入
失敗則保留舊資料。此工具不查詢完整明細、不呼叫 AI，也不修改 MMIS 系統資料。

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
