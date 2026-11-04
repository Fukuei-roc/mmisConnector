# 驗證報告

## 摘要

- 任務：同次匯出未簽核日檢工單清查 Excel
- 結果：自動化驗證通過，並從既有 SQLite 快照產生指定的第二份 Excel；Live MMIS 指令未執行
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_query_daily_inspection_work_orders_not_submitted.py tests/test_unclosed_ab_xlsx.py tests/test_export_unclosed_ab_fault_notices_from_db.py -ra -o addopts=''` | 通過 | 59 passed、2 skipped；兩項需本機錄製 DOM 的舊測試因 fixture 未提供而跳過。 |
| `python -m pytest tests/test_query_daily_inspection_work_orders_not_submitted.py -ra -o addopts=''` | 通過 | 欄寬調整後 25 passed、2 skipped。 |
| `python -m compileall -q tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py tests/test_query_daily_inspection_work_orders_not_submitted.py` | 通過 | 無語法錯誤。 |
| `git diff --check` | 通過 | 無空白錯誤；Git 提示部分檔案之後會轉換為 CRLF。 |
| Kanban JSON 解析 | 通過 | `epics.json` 與 `MMIS-051.json` 均可解析。 |
| 讀取輸出目錄的 `檢車室未填檢修人員日檢工單_程式產生1104.xlsx` | 通過 | 14 列資料、5 欄；12 pt 微軟正黑體、標題置中、資料靠左、列高 15.5。 |
| `python -c "from tools.mmis_development import query_daily_inspection_work_orders_not_submitted_for_approval as t; from tools.mmis_development._unclosed_ab_xlsx import configured_output_directory, read_snapshot; rows=read_snapshot(t.DATABASE_PATH,t.TABLE_NAME,t.DATABASE_FIELDS); t.export_unsigned_complement_xlsx(t.DATABASE_PATH,len(rows),configured_output_directory()/'檢車室未填檢修人員日檢工單_程式產生1104.xlsx')"` | 通過 | 使用既有 SQLite 快照呼叫匯出函式，實際建立 `未簽核日檢工單清查_程式產生1104.xlsx`，含 3 筆、9 欄；兩份工作單集合互斥，合併完整等於快照 16 筆。字型、字級、對齊與標題列高正確。 |
| 重新開啟 `未簽核日檢工單清查_程式產生1104.xlsx` 並讀取 A:I 欄寬 | 通過 | 實際檔案欄寬為 11.8、17.9、6.5、15.8、10.6、13.2、14.5、14.5、30。 |

## UI 證據

無 UI，螢幕截圖不適用。測試以 openpyxl 重新開啟暫存 XLSX，並直接重新開啟輸出目錄中的實際新檔，檢查欄位、資料、字型、對齊與列高。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 第二份以第一份實際 Excel 的工作單欄建立排除集合，並核對 SQLite 快照筆數 | 低 | 已檢查 |
| 第一份與第二份的資料列數相加等於測試快照總數，且補集保留未被第一份篩選收錄的工單 | 低 | 已由測試驗證 |
| 輸出沿用共用 XLSX builder 與獨占檔案建立，文字儲存格和同名檔保護沿用既有行為 | 低 | 已檢查 |
| 匯出器與既有 1104 檔案的九欄欄寬皆符合指定值 | 低 | 已由測試及實際工作簿讀回驗證 |

## 殘留風險

- 未執行 Live MMIS 查詢；實際第二份 Excel 使用既有 SQLite 快照產生，未更新快照。
- 兩項既有 DOM 測試因本機缺少錄製 fixture 而跳過，與本次 XLSX 差集邏輯無關。
