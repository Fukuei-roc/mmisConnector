# 驗證報告

- 變更：`run_daily_work.bat` 的 `STEP=link` 命令末尾增加 `--export-xlsx`；其他步驟及重試規則未修改。
- 精確命令比對：`batch command: exact match`。
- `python -m pytest tests/test_cli.py tests/test_auto_link_xlsx.py -q`：11 項通過。
- `git diff --check -- run_daily_work.bat`：通過。
- 審查：既有 CLI 接受該旗標；匯出錯誤會使 CLI 回傳非零碼，批次檔原有 `if errorlevel 1 goto :finish` 能攔截。
- 限制：依本次範圍未執行會連線 MMIS 的 `run_daily_work.bat`。無 UI 變更或螢幕截圖。
