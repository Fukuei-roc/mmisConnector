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
| 查詢未處理故障通報 | 無需輸入；取得本段未處理故障通報清單。 | `python -m tools.mmis_development.query_unprocessed_fault_notices` |
| 查詢未結案故障通報 | 無需輸入；取得新竹機務段 A、B 級未結案故障通報清單。 | `python -m tools.mmis_development.query_unclosed_fault_notices` |
| 查詢臨時檢修工單明細 | 輸入工作單號；取得工單基本資料、已勾稽故障通報、維修程序概況及試車報告。 | `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-41264` |
| 查詢故障通報完整資料（最完整） | 輸入通報號；取得基本資料、ATP 標記、段檢修與 CA 查修工單、故障分析，以及適用時的 ATP 分析。 | `python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14` |
| 查詢故障通報的故障分析 | 輸入通報號；取得事故現象、處理概況、故障原因、處理情形及改善對策。 | `python -m tools.mmis_development.query_fault_notice_analysis 1150828-12` |
| 查詢故障通報關聯的 ATP 故障分析 | 輸入已勾選 ATP 故障的通報號；取得故障要因、故障因子及故障項目。 | `python -m tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice 1150210-36` |
| 查詢故障通報關聯的工單 | 輸入通報號；取得關聯的段檢修工單清單。 | `python -m tools.mmis_development.query_work_orders_linked_to_fault_notice 1150910-14` |
| 查詢故障通報關聯的查修工單 | 輸入通報號；取得關聯的 CA 查修工單清單。 | `python -m tools.mmis_development.query_repair_work_orders_linked_to_fault_notice 1150930-09` |
| 依車號與日期查詢日檢工單 | 輸入車號與檢修日期條件；取得符合條件的日檢工單清單。 | `python -m tools.mmis_development.query_daily_inspection_work_orders_by_vehicle_and_date 717 '>2026/09/23'` |
| 依工作單號讀取明細 | 輸入日檢工作單號；取得該工單已勾稽的故障通報清單。 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number 115-1A-70048` |
| 查詢日檢檢修記錄備註 | 輸入日檢工作單號；JSON 的「檢修記錄」只包含 count 與 records，records 列出備註非空的裝置名稱、回報結果與備註。 | `python -m tools.mmis_development.query_daily_inspection_work_order_inspection_records 115-1A-71815` |
| 依工作單號勾稽故障通報 | 輸入日檢工作單號與通報號；將通報勾稽至工單並確認結果。 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number_and_link_fault_notice 115-1A-71002 1150923-36` |

最後一項會修改 MMIS 資料。只能在明確核准的受控 Live 驗證或人工單筆操作中使用；若
結果不明，先人工確認，不得直接重送。

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
