# 驗證報告：日檢工單待簽核人

## 摘要

- 任務：在日檢工單明細 CLI 加入「待簽核人」。
- 結果：通過；指定工單的即時查詢成功。
- 驗證者：Codex，2026-10-31。

## 指令與結果

| 指令 | 結果 |
|---|---|
| `python -m pytest tests/test_daily_inspection_inspection_records.py tests/test_temporary_repair_procedure.py -q` | exit 0；日檢與臨時檢修測試通過，缺少本機錄製檔的測試依既有條件跳過。 |
| `python -m pytest -q` | exit 0；完整測試通過，部分依賴外部錄製檔的測試跳過。 |
| `python -m tools.mmis_development.query_daily_inspection_work_order_details 115-1A-78885` | 透過子程序執行，exit 0；JSON `success=true`、工作單號一致、待簽核人 2 位，欄位緊接工作單狀態。驗證時只印摘要，未保存完整個資。 |
| `python -m compileall -q src tools/mmis_development tests` | exit 0。 |
| `python -m pip check` | exit 0；無損壞的套件相依。 |
| `git diff --check` | exit 0；只有工作樹換行符警告。 |
| `python -m ruff check ...` | 未執行；環境沒有安裝 `ruff`。專案未設定此 lint 工具。 |

## 審查

- 功能：核簽中才切換核簽頁簽；非核簽中回傳空陣列。解析共用原臨時檢修的完整分頁檢查、姓名去重與排序。
- 安全與隱私：沿用既有工作單號驗證與 HTTP session；只讀 MMIS，不寫入遠端資料或結果檔案。姓名只出現在使用者要求的 stdout JSON。
- 架構：共用核簽流程解析模組；架構依賴清單已登記新增模組。
- UI 證據：不適用，沒有 UI 變更。

## 殘留風險

- 本機缺少部分外部錄製檔，相關歷史測試跳過。指定工單的 live CLI 已驗證核簽頁面。
- 其他未抽查的日檢工單若使用不同核簽表格布局，解析會報錯而不回傳部分名單。
