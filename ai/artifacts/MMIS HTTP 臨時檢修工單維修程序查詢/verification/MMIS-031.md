# 驗證報告

## 摘要

- 任務：MMIS-031 已勾稽故障通報清單
- 結果：通過，待人工驗收
- 驗證者：Codex

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q` | 通過 | 15 項測試，含 C1 錄製 1 筆通報、C2 錄製空清單、分頁不完整拒絕回傳、JSON 鍵順序 |
| `python -m pytest -q` | 通過 | 全套測試；既有部分案例依環境跳過 |
| `python -m compileall -q src tools/mmis_development tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 無 whitespace 錯誤 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C1-41264` | 通過 | `已勾稽故障通報.count=1`；通報號 `1151005-29`、日期 `2026/10/03`、車號 `EMA815`、事故等級 `A`；原紀事仍 1 筆 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C2-41266` | 通過 | `已勾稽故障通報.count=0`、`records=[]`；原紀事仍 3 筆 |

## 審查發現

- 臨時檢修明細的「故障通報管理」表格與日檢工單同名且表頭一致，可重用共用表格解析與單頁完整性檢查。
- C1 表格還有第五欄 `事故等級`；共用解析保留全部五欄。
- PowerShell 終端的預設 cp950 會讓臨時除錯輸出看似亂碼；檢查 Python 字串與 CLI 的 UTF-8 JSON 後，確認來源中文完整，無需位置式解析。
- `工作單狀態`、`已勾稽故障通報`、`維修程序概況` 的 JSON 鍵順序已驗證。

## 安全性與殘留風險

- 沿用現有 session 與唯讀事件，從已開啟的工單明細讀取表格；未新增 MMIS 寫入或額外登入。
- 多頁已勾稽通報沒有實例；目前與日檢 reader 一樣在資料超過單頁時明確失敗，避免輸出不完整清單。後續如有多頁工單，由維護者補分頁能力與錄製測試。
- 無 UI 變更，螢幕截圖不適用。
- `mmis-dev-knowledge` 的 `commonErrors/maximo-page-count-must-match-target-table` 已合併此次臨時檢修工單的故障通報表格實例；無條目被棄用。

## 後續任務

- 取得多頁已勾稽故障通報實例後，可新增完整分頁擷取。
