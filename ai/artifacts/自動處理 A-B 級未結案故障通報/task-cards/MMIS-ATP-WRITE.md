# AI-Ready 任務卡

## Metadata

- 任務：MMIS-ATP-WRITE 自動填寫 ATP 故障分析並註記成功項目
- 上層規格：`ai/artifacts/自動處理 A-B 級未結案故障通報/feature-spec.md` 第十八階段
- 上層 Epic：自動處理 A-B 級未結案故障通報
- 上層 User Story：符合一般故障分析條件時補齊 ATP 故障分析
- 分軌：後端
- 前置任務（dependsOn）：無；ATP 查詢、選項樹與一般分析寫入已實作
- 狀態：完成（離線驗證；正式 MMIS 寫入待人工驗收）
- 風險等級：高，MMIS 遠端寫入與本機 SQLite 更新
- Agent owner：Codex
- 人工核准者：使用者於本次對話明確要求開始修改程式

## 目標

當一般故障分析候選通報也缺 ATP 分析時，按 2026-10-28 錄製填寫 ATP 三欄，儲存並回讀確認，逐項在 SQLite 備註追加成功標記。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`、`query_fault_notice_full_detail.py`、`src/mmis_connector/fault_notices/{atp_reader,atp_ai_analysis,analysis_writer}.py`、`src/mmis_connector/parser.py`、相關測試與外部 ATP 填寫錄製。
- 既有模式：精確通報號查詢、動態 label/for target、三次 setvalue 且最後一次與 SAVE 同 POST、成功訊息及獨立回讀、SQLite `BEGIN IMMEDIATE`。
- 假設：`備註` 指本機 SQLite 欄位；ATP 三欄全空才執行 ATP 寫入；本次快照完成標記仍於下次全量同步重置。
- 未知事項：部分 ATP 欄位已有值時的 MMIS 相依欄位行為，故本卡不修改這類 ATP 分析。
- 允許變更的檔案：上述 source、對應測試、架構檔案清單測試與 Production source inventory、此 Epic 規格與驗證報告、工具 README。
- 不得觸碰：正式 SQLite、錄製 HAR/DOM、憑證、無關模組與唯讀範本。

## 需求

- ATP 三欄全空時，AI 產生並驗證兩份內容後才開始任何 MMIS 寫入；部分填寫時僅需驗證一般分析內容。
- ATP 三欄全空時先寫 ATP，逐項回讀確認後追加備註，再寫一般分析並追加備註。
- ATP 三欄部分已有值時跳過 ATP 寫入，一般分析照常執行並回報 ATP 未完成。
- 保留當次既有備註文字，不重複追加相同標記。不得對結果不明的 MMIS POST 自動重送。

## 驗收標準

- 錄製中的動態 input target、事件順序、儲存回應及最終 DOM 可由離線測試核對。
- 兩項都成功時備註含 `已填寫ATP故障分析` 與 `已填寫故障分析`；只成功一項時僅含對應標記。
- ATP 已完整、部分填寫、AI 建議錯誤、儲存結果不明與回讀不符各有明確安全行為。
- 現有一般故障分析與 Excel 輸出測試通過。

## 實作備註

- 不新增資料表或變更 SQLite schema。沿用單次快照與既有查詢入口。

## 驗證契約

- 單元測試：ATP writer、備註追加與批次部分成功分支。
- 整合測試：錄製回應解析、暫存 SQLite 批次。
- E2E 測試：不執行正式 MMIS 寫入；僅執行離線測試。
- 型別檢查：不適用，專案無專用 typecheck gate。
- Lint：專案既有 Python 檢查。
- Build：`python -m compileall` 針對變更模組。
- 螢幕截圖：無 UI 變更，錄製最終 DOM 作行為證據。
- 安全性檢查：確認不輸出 HAR 敏感值、不重送寫入 POST、不覆蓋部分既有 ATP 分類。

## 完成證據

- 變更的檔案：`src/mmis_connector/parser.py`、`src/mmis_connector/fault_notices/atp_writer.py`、`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`、相關測試、README、架構清單與本 Epic 產出物。
- 執行過的指令：`python -m pytest -q`、`python -m pytest -q tests/test_write_atp_fault_notice_analysis.py -rs`、`python -m compileall -q ...`、`git diff --check`。
- 測試輸出：以上指令 exit 0，詳細結果見 `verification/MMIS-ATP-WRITE.md`。
- 螢幕截圖：不適用。
- 已知限制：部分已有值的 ATP 分析不自動填寫；快照備註下次同步重置。
- 後續任務：取得部分填寫錄製後另立任務。
