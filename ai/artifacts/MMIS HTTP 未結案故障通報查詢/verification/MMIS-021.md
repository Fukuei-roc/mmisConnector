# 驗證報告

## 摘要

- 任務：MMIS-021 HTTP-only 未結案故障通報零參數查詢工具
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest -q tests/test_query_unclosed_fault_notices.py ...` | 通過 | 動態 target、事件、零筆、31 筆兩頁、錄製 DOM、tool 與既有回歸 |
| `python -m pytest -rs` | 通過 | 138 passed、4 skipped；skip 皆為其他功能缺少各自本機 recording fixture |
| `python -m compileall -q src tests tools/mmis_development` | 通過 | 無語法／bytecode compilation 錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check -- . ':(exclude)mmis-post-feature-refactoring-guide.md'` | 通過 | 排除使用者既有、不屬於本任務的修改 |
| 安全／依賴 `rg` 掃描 | 通過 | 新 runtime 無瀏覽器、subprocess、錄製檔或檔案寫入；production 無 tools import |
| 第一次唯讀 live 命令 | 安全失敗 | filterrows 局部回應不含 toolbar 查詢名稱；程式以非零 exit code 停止，未輸出部分資料 |
| 錄製 HAR 回應形狀檢查 | 通過 | 最終 XHR 含表格／1-20/31，但不含 saved-query toolbar 名稱 |
| 修正後唯讀 live 命令 | 通過 | exit code 0；query／filters 正確；count=31、records=31、17 欄位 |

## UI 證據

| Viewport | 螢幕截圖 | 備註 |
|---|---|---|
| 不適用 | 不適用 | 本專案無 UI 變更；外部錄製截圖僅作只讀分析 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 最終 filterrows XHR 是局部表格片段，不重複包含 saved-query 名稱 | 中 | 已修正；query 名稱在前一步驗證，最後片段驗證 schema／分頁／筆數 |
| 安全性、隱私、認證、架構偏移或檔案副作用 | 無 | 未發現問題 |

## Security / Maintainability Review

發現的問題：無未解決問題。

- 功能正確性：錄製結構、離線 31 筆兩頁與 live 31 筆一致。
- 安全性／隱私：未輸出或提交憑證、cookie、token、session state、原始 response 或內部資料列；命令唯讀。
- 架構：重用 `MMISSession`、`MaximoEventClient`、parser 與同 domain 私有共用基底；wrapper 無 domain logic。
- 可維護性：prefix 與欄位編號動態解析；既有公開 API 與測試保持通過。
- 核准建議：核准。

## 殘留風險

- MMIS 若更名 saved query、必要表頭或改變 list event／pagination DOM，命令會 fail closed，需要更新 parser 或 protocol mapping。
- 固定查詢條件刻意不參數化；需求變更時需另立任務。
- 四個其他功能的 optional recording tests 仍因其各自外部 fixture 不存在而 skip，與本功能無關。
- 本功能不建立檔案；完整 JSON 只印到使用者終端，資料保護責任沿用既有內部操作規範。

## 完成定義

- 實作、離線測試、完整回歸、build／dependency check、安全審查、錄製證據與唯讀 live 驗證皆已完成。
- 符合 definition of done。
