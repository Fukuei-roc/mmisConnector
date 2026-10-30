# AI-Ready 任務卡

## Metadata

- 任務：同步待簽核段修工單號至 SQLite。
- 上層規格：`feature-spec.md` 第二十階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：後續能從資料庫匯出所有待簽核工單。
- 分軌：後端。
- 前置任務：無。
- 狀態：完成。
- 風險等級：高，涉及既有資料庫 schema 遷移。
- Agent owner：Codex。
- 人工核准者：使用者本次明確需求。

## 目標

讓完整通報中的核簽中段修工單號可由資料庫直接讀取。

## 情境包（Context Pack）

- 相關檔案：`auto_process_unclosed_ab_fault_notices.py`、`export_unclosed_ab_fault_notices_from_db.py`、對應測試、工具 README。
- 既有模式：全量 snapshot 後逐筆更新明細；嚴格驗證 schema；Excel 匯出核對完整 SQLite schema 但只輸出九欄。
- 假設：僅精確狀態「核簽中」列入；多筆以 JSON 陣列文字保存，零筆為 SQL NULL。
- 未知事項：正式 MMIS 在下次執行時的通報與工單資料。
- 允許變更：上述工具、測試、README、本 Epic 規格與驗證產出物。
- 不得觸碰：MMIS 查詢及寫入元件、既有正式資料庫、使用者未追蹤檔案。
- 情境預算：已讀專案地圖、流程、DoR、DoD、同步與匯出模組及相關測試；未讀無關 MMIS 元件。

## 需求與驗收標準

- 新欄緊接備註；既有 15 欄庫可在交易內遷移。
- 待簽核為 true 時，只保存「核簽中」工單的全部單號，依來源順序去重，JSON 可解析。
- 零筆與 false 儲存 SQL NULL；缺失資料報錯，不誤存空結果。
- 重跑同步重算；原有 Excel 九欄維持一致。

## 實作與驗證契約

- 在 `replace_rows` 交易中先核對舊 schema 再遷移；逐筆更新時與六欄檢查值同交易寫入。
- 離線 pytest 驗證舊庫遷移、多筆、零筆、錯誤資料、同步及 Excel 回歸。
- 不執行可能寫入 MMIS 的正式指令；CLI 無 UI 螢幕截圖。
- 執行 `python -m pytest`、編譯及 `git diff --check`；審查交易與資料驗證。

## 完成證據

- 變更的檔案：同步工具、離線匯出器、兩支相關測試、README、規格、任務卡及驗證報告。
- 執行過的指令：`python -m pytest -q`、`python -m compileall -q`、`git diff --check`。
- 測試輸出：完整套件 exit code 0；遷移、回滾、JSON 工單、同步與 Excel 回歸均通過。
- 螢幕截圖：CLI 與 SQLite 無 UI。
- 已知限制：未執行會連線並可能寫入 MMIS 的正式同步；現有正式 SQLite 需在下次同步時遷移並取得當時工單。
- 後續任務：待簽核工單獨立匯出功能。
