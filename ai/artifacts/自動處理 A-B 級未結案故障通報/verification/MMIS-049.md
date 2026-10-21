# 驗證報告

## 摘要

- 任務：MMIS-049 完成同步後匯出 XLSX
- 結果：離線驗證通過；未執行 Live MMIS 或正式 OneDrive 匯出
- 驗證者：Codex

## 指令與結果

| 指令 | 結果 |
|---|---|
| `python -m pytest tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py` | 79 passed |
| `python -m pytest` | 431 passed, 39 skipped |
| `python -m compileall -q src tests` | 通過 |
| `python -m compileall -q tools/mmis_development` | 通過 |
| `python -m pip check` | No broken requirements found |
| `git diff --check` | 通過；僅 Windows 換行提示 |

## 審查

- 同步順序：共用既有 `execute()`，MMIS 查詢與 SQLite commit 均完成後才唯讀 SQLite 並匯出。`partial_success` 或同步例外均不匯出。
- 資料完整性：schema 欄名與 15 欄順序核對，匯出筆數須與本次同步結果一致；Boolean 僅依指定七欄的 1/0/NULL 轉型。
- 檔案安全：`xb` 排他建立檔名，並發測試產生不同序號；寫入失敗清除本次新建的不完整檔案，不動既有檔案。
- 資料安全：字串寫為 XLSX 文字型別，避免 `=`、`+`、`-`、`@` 公式注入；不修改 SQLite 原值。
- 格式：openpyxl 讀回驗證單張工作表、字型、12 pt、對齊、欄寬、換行與列高。
- 錯誤界線：匯出路徑缺失、資料夾不存在或檔案寫入失敗時，已提交 SQLite 保留並以非零 exit code 區分同步與匯出狀態。
- 架構：只新增 Development Tool helper；架構測試將 helper 排除於可執行工具計數，Production CLI 未修改。

## 已知限制

- 未執行 Live MMIS 或 OneDrive 正式匯出；外部系統權限與網路條件仍需實際驗收。
- Excel 單列高度上限為 409.5 pt，極長文字仍可能需要人工展開列高檢視。
