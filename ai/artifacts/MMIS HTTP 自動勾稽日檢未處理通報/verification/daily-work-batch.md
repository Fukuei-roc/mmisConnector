# 驗證報告

## 摘要

- 任務：根目錄 `run_daily_work.bat`（原名 `每日工作自動執行.bat`）
- 結果：部分通過。批次檔與真實執行通過；第一個 Python 入口的單筆查詢錯誤可能以退出碼 0 結束，批次檔無法識別並重試。
- 驗證者：Codex；另由獨立審查 agent 檢查安全性與正確性。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `cmd.exe /d /c "call 每日工作自動執行.bat"`，假 `python.cmd`，改名前 | 通過 | 立即重試 3 次呼叫；第二步兩次失敗後第三次成功，共 4 次呼叫、耗時 2458 ms；三次均失敗時回傳 1 並顯示最終錯誤；非網路錯誤與含 `ConnectionError` 字樣的其他 JSON 欄位均只呼叫一次。 |
| `cmd.exe /d /c "call 每日工作自動執行.bat"`，沙箱內，改名前 | 預期限制 | 第一項成功，9 筆均無對應日檢工單；第二項 SQLite 同步成功，但工作區外 XLSX 寫入遭 `PermissionError`，批次檔回傳 1。 |
| 同上，經授權在沙箱外執行 | 通過 | 第一項成功、9 筆無對應工單、無失敗；第二項同步 11 筆，兩份 XLSX 匯出成功，批次檔回傳 0。 |
| 檢查兩份輸出檔 `is_file()` | 通過 | A/B 通報與優先簽核 XLSX 均存在。 |
| `git diff --no-index --check -- NUL run_daily_work.bat` | 通過 | 無空白格式警告；退出碼 1 表示新檔與 NUL 有差異。 |
| `cmd.exe /d /c "call run_daily_work.bat"`，假 `python.cmd`，改名後 | 通過 | 兩個指令均依序呼叫，退出碼 0；原檔名不存在，新檔名存在。 |

## UI 證據

不適用；沒有 UI 變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| `auto_link/orchestrator.py` 將單筆查詢網路錯誤記入 SQLite 的 `query_failed`，整體仍可回傳成功；批次檔無法由退出碼辨識。 | 中 | 已記錄為既有契約限制；本任務不修改 Python 業務邏輯。 |
| 合併輸出可能含無關的 `ConnectionError` 字樣。 | 低 | 已改為解析 JSON 的 `message` 並比對明確連線錯誤；假指令測試已覆蓋誘餌欄位。 |

## 殘留風險

- 批次檔只能重試整個 Python 指令以非零退出碼呈現的明確 MMIS transport 失敗。第一項的單筆 `query_failed` 需檢視 JSON 與 SQLite 結果，若要自動辨識須另核准 Python 結果契約變更。
- 真實測試已建立本機 SQLite 執行紀錄與兩份 XLSX。第一項未勾稽任何工單，第二項未寫入故障分析。
- 沒有測到真實網路中斷，重試時序以假 `python.cmd` 驗證。
