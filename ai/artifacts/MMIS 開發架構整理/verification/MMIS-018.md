# 驗證報告

## 摘要

- 任務：分離 production CLI 與 MMIS development tools
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| 修改前 `python -m pytest` | 通過 | 121 passed、3 skipped |
| `python -m pytest tests/test_cli.py tests/test_development_tools.py tests/test_architecture.py -q` | 通過 | 20 passed |
| 四個 development module 的無網路錯誤參數 `python -m` 執行 | 通過 | 全部可 import，輸出 JSON usage error，未載入設定或登入 |
| 修改後 `python -m pytest` | 通過 | 128 passed、3 skipped；淨增 7 項 |
| `python -m compileall -q src tests` | 通過 | exit 0 |
| `python -m compileall -q tools/mmis_development` | 通過 | exit 0，額外覆蓋新工具 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `python -m mmis_connector` | 通過預期契約 | exit 1；available commands 只列 production auto-link |
| `git diff --check` | 既有檔案造成非零 | 只回報本任務前已修改的 `Prompt.md` 兩處 trailing whitespace |
| `git diff --check -- . ':(exclude)Prompt.md'` | 通過 | 本任務 tracked diff 無 whitespace error |

3 個 skip 都是既有 optional external recorded-DOM tests；本次未新增 skip，也未執行任何
Live MMIS command。

## UI 證據

不適用；專案為 CLI，本次沒有 UI 變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| `src/mmis_connector/` 只有 `cli.py` 改變；所有 reusable／business modules 零變更 | 資訊 | 通過 |
| Production modules 沒有 import `tools`、development、reference 或 examples | 資訊 | 通過 |
| Development tools 沒有複製 event、parser、page state、SQLite 或 protocol implementation | 資訊 | 通過 |
| 四個 tools 直接 import 正式 components，且不 import production CLI | 資訊 | 通過 |
| 單筆勾稽 tool 有明確 mutation／不重送警示 | 資訊 | 通過 |
| 新增內容沒有憑證、cookie、token、session ID 或私鑰 | 資訊 | 通過 |

安全性與可維護性審查未發現需修改事項；核准建議為「核准」。

## 殘留風險

- 移除四個正式 CLI routes 是需求指定的 breaking interface change；repository 外的人工腳本
  若仍使用舊命令，需改成 `python -m tools.mmis_development...`。
- Development tools 是 repo-local package，預期從 repository root 執行，不隨
  `mmis-connector` console script 安裝成正式 commands。
- Import boundary 是靜態 AST 測試；若未來合理新增 tool 或 dependency，需同步更新測試。
- 原始 `git diff --check` 仍受使用者既有 `Prompt.md` 尾端空白影響，本任務未修改該檔。
