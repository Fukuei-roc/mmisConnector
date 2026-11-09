# AI-Ready 任務卡

- 目標：每日批次的自動勾稽步驟傳入 `--export-xlsx`。
- 核准：使用者於 2026-11-09 明確要求。
- 範圍：只改 `run_daily_work.bat` 中的 `STEP=link` 命令與本卡驗證紀錄。
- 情境包：批次檔以 `call :run` 執行 CLI；成功檢查讀取 JSON，CLI 匯出失敗會回傳非零錯誤碼。既有 CLI 已支援該選項。
- 非目標：不改其他步驟、重試規則、MMIS 查詢與 Excel 格式。
- 風險：低；執行每日批次時會多輸出一份 Excel。
- 驗收：命令列精確包含 `--export-xlsx`，其餘批次邏輯不變。
- 驗證：精確比對批次命令、`git diff --check`、CLI 與匯出器針對性測試。不執行會連線 MMIS 的批次檔。
