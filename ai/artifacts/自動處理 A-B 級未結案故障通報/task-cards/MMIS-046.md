# AI-Ready 任務卡

## Metadata

- 任務：MMIS-046 查詢首筆通報並回填六個結案狀態檢查值
- 上層規格：[feature-spec.md](../feature-spec.md)
- 上層 Epic：自動處理 A-B 級未結案故障通報
- 上層 User Story：查詢首筆通報結案狀態檢查
- 分軌：後端
- 前置任務（dependsOn）：MMIS-045（完成）
- 狀態：完成
- 風險等級：高（本機資料庫更新、可能呼叫付費 AI）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-20 指定功能；付費 AI 只在明確旗標下啟用）

## 目標

保留既有完整 snapshot；成功後只用來源第一筆通報號呼叫既有完整通報查詢，回填六個檢查欄位。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`、`tools/mmis_development/query_fault_notice_full_detail.py`、`src/mmis_connector/fault_notices/full_detail.py`、`tests/test_auto_process_unclosed_ab_fault_notices.py`。
- 既有模式：完整通報工具的 Python `execute(args)` 可直接呼叫；結果以 `結案狀態檢查` 包含六欄。
- 假設：第一筆指本次未結案查詢 `records[0]`，資料庫保留全部來源列。
- 未知事項：第一欄預設固定 `null`；加 `--check-analysis-readiness` 會呼叫付費 OpenAI。本次預設不啟用 AI，保留明確 opt-in。
- 允許變更的檔案：新工具、相關離線測試、Development Tool README、本 Epic 規格與治理產出物。
- 不得觸碰：根 README、Production CLI、HTTP event、authentication、parser、retry policy。
- 情境預算備註：只讀現有 snapshot、完整通報工具、Reader、相關測試及流程文件；跳過不相關 UI 與 Production mutation。

## 需求

- 成功建立 snapshot 後查詢第一筆；零筆則不查明細。
- 以通報號核對明細回應，驗證六欄名稱與布林／NULL 型別，再以獨立 transaction 更新單筆。
- 明細或更新失敗時保留已完成 snapshot；JSON 明確區分 snapshot 與明細階段。
- 不呼叫 `--ai-analysis`，不修改 MMIS，不處理第二筆以後。

## 驗收標準

- 第一筆六欄與既有完整通報結果一致，其他筆六欄與備註保持 NULL。
- 查詢僅呼叫一次；缺欄、通報號不符、型別錯誤、SQL 失敗均不得寫入部分檢查值。
- 空 snapshot 成功且不發出明細查詢。

## 實作備註

- Python 函式直接重用既有完整通報工具；不使用 subprocess 或 CLI 文字解析。
- 預設不啟用 AI；使用者可明確加入 `--check-analysis-readiness` 啟用。

## 驗證契約

- 單元測試：`python -m pytest tests/test_auto_process_unclosed_ab_fault_notices.py`
- 整合測試：`python -m pytest`
- E2E 測試：本階段離線 mock，不自行執行 Live MMIS
- 型別檢查：不適用
- Lint：`git diff --check`
- Build：`python -m compileall -q src tests tools/mmis_development`
- 螢幕截圖：不適用
- 安全性檢查：SQL 參數化、通報號核對、AI 開關明確、失敗保留資料

## 完成證據

- 變更檔案：新工具、離線測試、Development Tool README、Epic 規格與治理產出物。
- 執行過的指令與輸出：見 [MMIS-046 驗證報告](../verification/MMIS-046.md)。
- 螢幕截圖：不適用。
- 已知限制：未執行 Live MMIS；舊資料庫需重跑新程式。
- 後續任務：如需批次處理全部通報，再建立新的任務卡。
