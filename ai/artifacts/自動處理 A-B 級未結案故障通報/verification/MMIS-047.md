# 驗證報告

## 摘要

- 任務：MMIS-047 逐筆查詢並保存等候結案的 A 級通報
- 結果：通過（離線）；Live MMIS 未執行
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_auto_process_unclosed_ab_fault_notices.py` | 通過 | 50 passed |
| `python -m pytest` | 通過 | 401 passed, 39 skipped |
| `python -m compileall -q src tests` | 通過 | 無輸出 |
| `python -m compileall -q tools/mmis_development` | 通過 | 無輸出 |
| `python -m pip check` | 通過 | No broken requirements found. |
| `git diff --check` | 通過 | 僅 Windows 換行提示 |

## UI 證據

| Viewport | 螢幕截圖 | 備註 |
|---|---|---|
| 不適用 | 不適用 | 無 UI 變更 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 兩個 SQLite 間若分別 commit，失敗時可能重複或遺失通報 | 高 | 使用 `ATTACH DATABASE`，單筆插入與刪除同一 transaction；離線注入失敗驗證 rollback |
| SQLite WAL 不能保證跨附加資料庫的 crash atomicity | 中 | 搬移前檢查兩庫 journal mode，遇 WAL 時拒絕搬移 |
| 已等候結案通報若先寫主 snapshot，會被重查 | 中 | 完整驗證來源後先載入等候結案通報號，再篩除並寫主 snapshot |

## 殘留風險

- 未自行執行 Live MMIS；完整明細查詢逐筆建立新 session，實際執行時長待受控驗證。
- 若某筆查詢中途失敗，前面成功處理的列及等候結案搬移會保留；錯誤 JSON 回報已處理筆數與搬移筆數，下次重跑會跳過已等候結案者。
- 明確使用 `--check-analysis-readiness` 會對每筆待處理通報呼叫付費 OpenAI API；預設不呼叫。
