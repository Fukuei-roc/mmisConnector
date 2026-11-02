# AI-Ready 任務卡

## Metadata

- 任務：根目錄每日工作批次檔
- 上層規格：使用者 2026-11-02 明確指定的兩項指令與重試時序
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：以單一命令執行與檢視結果
- 分軌：不適用
- 前置任務（dependsOn）：無
- 狀態：審查中
- 風險等級：高（執行既有 MMIS 寫入與工作區外 Excel 匯出）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-11-02，直接指定實作並允許執行兩個指令）

## 目標

從根目錄的 `run_daily_work.bat` 依序執行自動勾稽與 A/B 級通報同步匯出。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/cli.py`、`src/mmis_connector/auth.py`、`src/mmis_connector/auto_link/orchestrator.py`、`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`、新批次檔。
- 既有模式：Python 入口輸出 JSON，失敗回傳 1；MMIS transport 錯誤訊息包含例外類型；auto-link 使用 SQLite 續跑並禁止自動重送不確定的勾稽。
- 假設：只對明確的 MMIS transport 失敗重跑整個指令；每個指令最多執行三次。
- 未知事項：第一個指令會把部分單筆查詢失敗記入 SQLite 並回傳 0；批次檔無法從退出碼區分該情況。
- 允許變更的檔案：根目錄批次檔與本任務的流程產出物。
- 不得觸碰：Python 業務邏輯、MMIS 資料結構與其他未關聯檔案。
- 驗證指令：以假 `python.cmd` 驗證順序、次數、延遲與退出碼；實際執行批次檔；`git diff --check`。

## 需求

- 第一項成功才執行第二項。
- 明確 MMIS 連線失敗時立即再試；第二次仍為連線失敗時等待一秒再試第三次。
- 非連線錯誤不重試；最後一次才顯示錯誤，並保留非零退出碼。
- 可從其他工作目錄啟動，執行時先切到專案根目錄。

## 驗收標準

- 模擬連線錯誤、非連線錯誤及成功路徑皆符合次數與順序。
- 真實執行時兩個指令均完成，XLSX 匯出成功並回傳 0。

## 實作備註

- 重試狀態以 `ATTEMPT`、`RESULT` 與當次輸出暫存檔表示。
- 解析指令輸出的 JSON `message`，只比對 `MMISSession` 的明確連線錯誤；保留原 Python 的遠端寫入確認與續跑機制。

## 驗證契約

- 單元測試：不適用，批次檔直接以假 `python.cmd` 做行為測試。
- 整合測試：四種模擬情境與一次真實執行。
- E2E 測試：使用者已授權真實執行。
- 型別檢查：不適用。
- Lint：`git diff --check`。
- Build：不適用。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：確認僅重試明確連線例外；臨時輸出刪除；不記錄憑證。

## 完成證據

- 見 `verification/daily-work-batch.md`。
