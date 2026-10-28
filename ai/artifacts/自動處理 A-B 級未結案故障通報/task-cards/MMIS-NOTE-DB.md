# AI-Ready 任務卡

## Metadata

- 任務：將故障通報備註規則移入 SQLite 同步流程。
- 上層規格：`feature-spec.md` 第十九階段。
- 上層 Epic：自動處理 A-B 級未結案故障通報。
- 上層 User Story：同步後在資料庫與 Excel 取得一致的備註。
- 分軌：後端。
- 前置任務（dependsOn）：無。
- 狀態：完成。
- 風險等級：高。本機資料庫全量替換與 MMIS 寫入續跑條件有關。
- Agent owner：Codex。
- 人工核准者：專案使用者透過本次明確需求核准。

## 目標

同步指令直接寫入規則備註，匯出器只讀取資料庫備註。

## 情境包（Context Pack）

- 相關檔案：`auto_process_unclosed_ab_fault_notices.py`、`export_unclosed_ab_fault_notices_from_db.py`、`_unclosed_ab_xlsx.py` 及其對應測試。
- 既有模式：六個狀態欄以完整 tuple 對照規則；SQLite 全量替換後逐筆更新狀態；分析成功後追加完成標記。
- 假設：使用者本次保留既有完成標記的要求，取代先前每次同步清空標記的規格。
- 未知事項：正式 MMIS 查詢後各通報的實際狀態；測試以隔離資料驗證。
- 允許變更的檔案：上述三個模組、對應測試、本 Epic 的規格、任務卡與驗證報告。
- 不得觸碰：MMIS HTTP 元件、資料庫 schema、正式資料庫內容及使用者未追蹤檔案。
- 情境預算備註：已讀專案地圖、架構與搜尋指南、流程、DoR、DoD、相關程式、測試及先前任務卡；未讀無關查詢模組。

## 需求

- 預設同步與加 `--export-xlsx` 的同步都寫入精確匹配的規則備註。
- 保留同一通報既有的兩種分析完成標記，不重複追加。
- 規則備註不能令待分析通報跳過 AI 流程。
- 匯出器從 SQLite 備註欄直接生成原格式的 Excel。
- 移除不再使用的匯出列改寫程式。

## 驗收標準

- 規則命中與不命中的 SQLite 值符合原匯出規則。
- 已有完成標記跨全量同步仍存在，並且狀態規則不覆蓋它們。
- 新產生的狀態備註不阻止符合條件的分析寫入。
- XLSX 九欄及原格式維持一致，備註與 SQLite 相同。
- 獨立匯出不修改 SQLite。

## 實作備註

- `replace_rows()` 先刪除再插入資料，必須在交易中保留同通報的完成標記。
- 資料充分性可在初次明細查詢後才寫入；備註規則須以最後六欄狀態計算。

## 驗證契約

- 單元測試：規則表精確比對、完成標記保留、分析候選條件。
- 整合測試：隔離 SQLite 同步並讀回 Excel，核對格式及備註。
- E2E 測試：不執行會連線及寫入 MMIS 的正式指令。
- 型別檢查、Lint、Build：專案未設定獨立指令；執行 pytest、編譯及 `git diff --check`。
- 螢幕截圖：不適用於 CLI 與 Excel；讀回活頁簿儲存格驗證。
- 安全性檢查：審查全量替換、交易回滾及分析寫入候選條件。

## 完成證據

- 變更的檔案：三個工具模組、三個對應測試、功能規格及本任務的驗證報告。
- 執行過的指令：`python -m pytest -q`、`python -m compileall -q tools/mmis_development/auto_process_unclosed_ab_fault_notices.py tools/mmis_development/export_unclosed_ab_fault_notices_from_db.py tools/mmis_development/_unclosed_ab_xlsx.py`、`git diff --check`。
- 測試輸出：完整 pytest 套件 exit code 0；獨立複審確認 ATP 成功而一般分析失敗後可續跑。
- 螢幕截圖：不適用。
- 已知限制：未執行正式 MMIS 同步。
- 後續任務：無。
