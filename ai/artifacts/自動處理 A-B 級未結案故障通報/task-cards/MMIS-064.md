# AI-Ready 任務卡

## Metadata

- 任務：MMIS-064 為含 ATP 故障分析未完成的狀態填寫 Excel 備註。
- 上層規格：`feature-spec.md` 第十七階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：完成同步後匯出 XLSX。
- 分軌：後端。
- 前置任務（dependsOn）：無。
- 狀態：完成。
- 風險等級：低。本機 XLSX 匯出規則；SQLite 唯讀。
- Agent owner：Codex。
- 人工核准者：專案使用者，透過本次明確需求核准。

## 目標

六欄狀態精確為 `(1,1,0,1,0,1)` 時，Excel「備註」填入「未處理（含ATP故障分析）」。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`、`tools/mmis_development/export_unclosed_ab_fault_notices_from_db.py`、`tests/test_export_unclosed_ab_fault_notices_from_db.py`、上層規格。
- 既有模式：同步指令呼叫離線匯出器；`STATUS_RULES` 以六欄 tuple 精確對應備註；未命中時保留原備註。
- 假設：以使用者提供的即時查詢六欄結果為準。本機舊快照同一通報的第一欄仍是 `NULL`。
- 未知事項：本次即時 MMIS 同步後，來源資料是否仍包含此通報。
- 允許變更的檔案：匯出器、對應測試、本 Epic 規格、本任務卡及驗證報告。
- 不得觸碰：MMIS 網路流程、SQLite 原始資料、其他使用者工作中的檔案。
- 情境預算備註：已讀專案地圖、流程、DoR、DoD、同步與匯出入口、相關測試及前一任務卡；跳過無關 MMIS 模組與完整網路錄製。

## 需求

- 只在 `(1,1,0,1,0,1)` 精確匹配時輸出指定備註。
- 保留其他規則與未命中時的 SQLite 原備註。
- 不寫回 SQLite，不變更同步或 MMIS 流程。

## 驗收標準

- 暫存 SQLite 中命中資料讀回 XLSX 後，備註為「未處理（含ATP故障分析）」。
- 相近但不相同的狀態維持原備註或原規則。
- 匯出前後 SQLite SHA-256 相同。

## 實作備註

- 既有 `STATUS_RULES` 無此六欄組合。本機快照共有 9 筆，沒有精確匹配；範例通報的本機六欄為 `(NULL,1,0,1,0,1)`。
- 延續現有 tuple 查表，不新增條件分支或抽象層。

## 驗證契約

- 單元及整合測試：隔離 SQLite 匯出並讀回 XLSX，涵蓋精確匹配、相近組合與 SQLite 不變。
- E2E 測試：不執行可能連線 MMIS 並寫入遠端的即時同步命令。
- 型別檢查、Lint、Build：此 Python CLI 未設定獨立指令；執行 pytest 與 `git diff --check`。
- 螢幕截圖：不適用；以 XLSX 儲存格讀回驗證。
- 安全性檢查：SQLite 唯讀，不處理憑證或新增網路呼叫。

## 完成證據

- 變更的檔案：匯出器、對應測試、本 Epic 規格、本任務卡及 `verification/MMIS-064.md`。
- 執行過的指令：`python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py -q`、`python -m pytest -q`、`git diff --check`。
- 測試輸出：相關測試和完整 pytest 套件 exit code 0；修正前指定案例實際為「原備註」，修正後為指定文字。
- 螢幕截圖：不適用於 CLI/XLSX；已讀回 XLSX 儲存格。
- 已知限制：未執行即時 MMIS 同步；本機快照與使用者提供的即時查詢第一欄不同。
- 後續任務：無。
