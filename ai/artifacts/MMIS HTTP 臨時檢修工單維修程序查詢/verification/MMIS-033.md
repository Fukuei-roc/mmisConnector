# 驗證報告

## 摘要

- 任務：MMIS-033 臨時檢修工單明細查詢指令更名
- 結果：通過
- 驗證者：Codex（2026-10-07）

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q` | 通過 | 19 項通過，包含新 `query_name` 與新用法斷言 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail` | 預期錯誤 | exit code 1；JSON 的用法訊息顯示新模組與 `<工作單號>` |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-41264` | 通過 | exit code 0；Live JSON：`success=true`、新 `query_name`、2 筆已勾稽故障通報、1 筆維修程序紀錄 |
| `python -m compileall -q src/mmis_connector/temporary_repair tools/mmis_development tests/test_temporary_repair_procedure.py` | 通過 | 無編譯錯誤 |
| `git diff --check` | 通過 | 無空白錯誤；Git 僅提示 Windows 換行轉換 |

## UI 證據

不適用；沒有 UI 變更。

## 審查發現

- 變更限於 CLI wrapper 名稱、顯示名稱、README、project map、測試與本次流程紀錄。
- 查詢事件、身分驗證、資料寫入與 JSON 資料欄位均未更動。
- 舊指令不再作為可執行模組；使用者需更新既有腳本或捷徑。

## 殘留風險

- MMIS Live 資料會變動；此次只驗證指定工作單當下的查詢結果。
- 舊驗證文件保留歷史指令與歷史輸出，作為當時證據。
