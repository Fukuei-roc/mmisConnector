# AI-Ready 任務卡

## Metadata

- 任務：每日工作批次檔顯示整體結果並等待 Q 關閉
- 上層規格：使用者 2026-11-02 指定的批次檔互動行為
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：以單一命令執行與檢視結果
- 分軌：不適用
- 前置任務（dependsOn）：無
- 狀態：完成
- 風險等級：中（只修改本機批次檔的結果判斷與視窗等待）
- Agent owner：Codex
- 人工核准者：專案使用者（本次明確要求）

## 目標

批次檔依兩個 Python 指令的退出碼及 JSON 結果判斷整體成功，顯示結果後等待 Q 鍵才結束。

## 情境包（Context Pack）

- 相關檔案：`run_daily_work.bat`、`src/mmis_connector/cli.py`、`src/mmis_connector/auto_link/orchestrator.py`、`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`。
- 既有模式：兩個指令輸出 JSON；第一項 `success=true` 仍可能有 `failed>0`；第二項 XLSX 狀態位於 `xlsx_export` 與 `priority_approval_xlsx_export`。
- 假設：第一項 `completed=true` 且 `failed=0`，第二項兩份匯出均為 `success`，才算全部成功。
- 未知事項：無阻擋事項。
- 允許變更的檔案：批次檔與本任務流程產出物。
- 不得觸碰：Python 業務邏輯、MMIS 寫入與 Excel 匯出實作。
- 驗證指令：以假 `python.cmd` 執行批次檔，使用互動終端測試 Q 鍵與退出碼；檢查 CRLF 與 diff。

## 需求與驗收標準

- 兩項指令都回傳成功退出碼，且各自 JSON 結果完整成功時，印出「所有程式正常執行完畢，沒有錯誤。」。
- 第一項有失敗筆數、第二項錯誤或任何匯出失敗時，印出失敗訊息，保留退出碼 1。
- 第一項未成功時不執行第二項。
- 成功與失敗後都停留在結果畫面；即使標準輸入被重新導向，其他鍵也不關閉，按 Q 鍵才結束。
- 原有連線錯誤重試行為維持。

## 驗證契約

- 行為測試：成功、第一項部分完成、第二項退出碼失敗、第二項 JSON 匯出狀態失敗。
- 互動測試：PTY 與標準輸入 `<NUL` 下等待、非 Q 鍵、Q 鍵與最終退出碼。
- E2E：不重跑 MMIS；本任務只改本機批次控制流程。
- Lint：`git diff --no-index --check -- NUL run_daily_work.bat`。
- 螢幕截圖：不適用，無圖形 UI；保留終端輸出作證據。

## 完成證據

- 見 `verification/daily-work-result-and-close.md`。
