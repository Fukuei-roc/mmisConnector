# AI-Ready 任務卡

## Metadata

- 任務：MMIS-061 段修工單已結案但分析未完成時填寫 Excel 備註。
- 上層規格：`feature-spec.md` 第十六階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：完成同步後匯出 XLSX。
- 分軌：後端。
- 前置任務（dependsOn）：無。
- 狀態：完成。
- 風險等級：低。本機 XLSX 匯出規則；SQLite 唯讀。
- Agent owner：Codex。
- 人工核准者：專案使用者，透過本次明確需求核准。

## 目標

六欄狀態精確為 `(0,0,1,0,0,0)` 時，Excel「備註」填入「未處理（段修工單結案）」。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/export_unclosed_ab_fault_notices_from_db.py`、`tests/test_export_unclosed_ab_fault_notices_from_db.py`、上層 `feature-spec.md`。
- 既有模式：`STATUS_RULES` 以六欄 tuple 對應備註；`annotate_row()` 僅轉換匯出資料列，未命中時保留原備註。
- 假設：六欄依 `DETAIL_CHECK_FIELDS` 順序組成；SQLite 資料充分性欄位為 `0`，其他指定欄位亦是整數 `0/1`。
- 未知事項：無。通報 `1151017-30` 的狀態來自使用者提供的唯讀查詢結果。
- 允許變更的檔案：匯出器、對應測試、本 Epic 規格、本任務卡與驗證報告。
- 不得觸碰：MMIS 網路流程、SQLite 原始資料、其他使用者工作中的檔案。

## 需求

- 只在 `(0,0,1,0,0,0)` 精確匹配時輸出指定備註。
- 保留 `(0,0,0,1,0,0)` 的「未處理」規則及未命中時原備註。
- 不寫回 SQLite，不變更同步或 MMIS 流程。

## 驗收標準

- 暫存 SQLite 中命中資料讀回 XLSX 後備註為「未處理（段修工單結案）」。
- 相鄰狀態 `(0,0,0,1,0,0)` 仍為「未處理」；其他未命中組合保留原備註。
- 匯出前後 SQLite SHA-256 相同。

## 實作備註

- 查重發現已完成的 MMIS-060 處理 `(0,0,0,1,0,0)`，與本任務第三欄、第四欄相反，不屬重複規則。
- 本任務只增加單一 `STATUS_RULES` 對應，沿用既有查表邏輯。

## 驗證契約

- 單元測試：匯出指定狀態、相鄰狀態及原備註，讀回實際 XLSX 儲存格。
- 整合測試：執行故障通報 XLSX 匯出測試。
- E2E 測試：不適用；避免執行可能呼叫 MMIS 與付費 AI 的即時同步命令。
- 型別檢查：不適用；Python 專案未設定獨立型別檢查器。
- Lint：不適用；Python 專案未設定獨立 lint 指令。
- Build：不適用；Python CLI 無建置步驟。
- 螢幕截圖：不適用於離線 CLI/XLSX 行為；讀回儲存格值驗證。
- 安全性檢查：沿用 SQLite 唯讀匯出與字串 literal 保護；不碰憑證或網路。

## 完成證據

- 變更的檔案：`tools/mmis_development/export_unclosed_ab_fault_notices_from_db.py`、`tests/test_export_unclosed_ab_fault_notices_from_db.py`、`feature-spec.md`、本任務卡與 `verification/MMIS-061.md`。
- 執行過的指令：`python -m pytest tests/test_export_unclosed_ab_fault_notices_from_db.py tests/test_unclosed_ab_xlsx.py tests/test_auto_process_unclosed_ab_fault_notices.py -q`、`python -m pytest -q`、`python -m compileall -q tools/mmis_development/export_unclosed_ab_fault_notices_from_db.py tests/test_export_unclosed_ab_fault_notices_from_db.py`、`git diff --check`。
- 測試輸出：相關測試與完整 pytest 套件通過；語法檢查及 diff whitespace 檢查通過。新增回歸測試在實作前曾按預期失敗。
- 螢幕截圖：不適用。
- 已知限制：未執行即時 MMIS 同步。
- 後續任務：無。
