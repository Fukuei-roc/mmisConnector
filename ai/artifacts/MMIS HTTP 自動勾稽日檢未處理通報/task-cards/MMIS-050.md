# AI-Ready 任務卡

## Metadata

- 任務：修復勾稽成功後確認失敗的批次狀態
- 上層規格：`ai/artifacts/MMIS HTTP 自動勾稽日檢未處理通報/feature-spec.md`
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：自動勾稽與中斷續跑
- 分軌：後端
- 前置任務：既有 auto-link 與 1A linker
- 狀態：完成
- 風險等級：高（遠端寫入結果核對、SQLite 狀態）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-21，本次明確要求修復及網路重試）

## 目標

對勾稽後的唯讀確認做有限重試，並在續跑時唯讀核對先前的 `link_error`，若 MMIS 已顯示指定通報則修正本機狀態為 `linked`。

## 情境包（Context Pack）

- 相關檔案：`daily_inspection/linker.py`、`daily_inspection/reader.py`、`auto_link/{orchestrator,store}.py` 與對應測試。
- 既有模式：同一 MMIS session、遠端寫入只送一次、寫入後依通報號精確驗證、逐列 SQLite commit。
- 已確認事實：SQLite 第 8 列 `1151018-06` 為 `link_error`，唯讀 live 查詢確認此通報已在工單 `115-1A-77246`。
- 未知事項：原始確認失敗的確切網路或頁面回應未保存，無法判定單次失敗的底層原因。
- 允許變更的檔案：上述四個 production 模組中必要檔案、對應 tests、本卡與驗證報告、同 Epic 功能規格。
- 不得觸碰：其他使用者的未提交變更、SQLite schema、憑證、遠端寫入重送機制。
- 驗證指令：針對性 pytest、完整 pytest、compileall、diff check、唯讀 live 查詢與受控 CLI 續跑。
- 情境預算備註：已讀專案地圖、架構地圖、搜尋指南、流程、DoR、DoD、linker、reader、orchestrator、store 與相關測試；跳過無關 MMIS 功能。

## 需求與驗收標準

- 勾稽寫入 POST 只送一次。確認查詢失敗或尚未看到通報時，最多重讀三次；只有完全相符的工作單與通報號可算成功。
- 續跑只核對有工作單號和通報號的 `link_error`；查到精確關聯才將本機狀態改為 `linked`，不呼叫 linker。
- 查證失敗或查無關聯時保留 `link_error` 和人工審查需求，不執行遠端寫入。
- 原批次第 8 列可在受控續跑後變為 `linked`，摘要不再顯示該筆 `link_error`。

## 實作與驗證契約

- 以既有 reader 執行唯讀核對，不另建 MMIS HTTP 協定。
- 測試涵蓋暫時失敗後確認、持續未確認、續跑核對成功及失敗、寫入永不重送。
- 不修改遠端資料來驗證；UI 與螢幕截圖不適用。
- 安全性：不得記錄帳密、cookie 或回應全文；仍以精確業務鍵核對。

## 完成證據

- 針對性測試、完整 pytest、compileall 與 diff check 通過。
- 唯讀 live 查詢確認 `1151018-06` 已存在於 `115-1A-77246`。
- 原批次受控續跑後，`linked=4`、`link_error=0`、`completed=true`；第 8 列仍只有一次勾稽嘗試。
- 獨立審查發現明細工作單身分缺口，已加入點開明細後的實際欄位驗證及錯明細測試；複審通過。
- 詳細證據與限制見 `verification/MMIS-050.md`。
