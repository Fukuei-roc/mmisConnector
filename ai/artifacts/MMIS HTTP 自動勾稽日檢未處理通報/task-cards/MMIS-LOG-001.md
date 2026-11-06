# AI-ready 任務卡

## Metadata

- 任務：auto-link CLI 執行紀錄。
- 上層規格：`../feature-spec.md` 的「執行紀錄增補」。
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報。
- 上層 User Story：內部使用者可從每次執行的紀錄還原查詢與勾稽過程。
- 分軌：後端。
- 前置任務：既有 auto-link CLI 已完成。
- 狀態：完成。
- 風險等級：中。
- Agent owner：Codex。
- 人工核准者：使用者於 2026-11-06 明確要求實作。

## 目標

每次有效執行產生獨立 JSONL，能以通報號與 `run_id` 追查查詢條件、結果與勾稽狀態。

## 情境包

見 `../architecture-plan-logging.md`。

## 需求與驗收標準

- 在 `logs/<命令名稱>/<UTC 日期>/` 建立每次執行獨立的檔案，其他命令可使用自己的子目錄。
- 記錄來源筆數、逐筆查詢條件、回傳筆數、候選工單摘要、選取與勾稽結果、安全化錯誤、批次完成資訊。
- stdout JSON、MMIS 寫入及 SQLite 續跑規則維持既有契約。
- Log 不含帳密、cookie、token、完整 MMIS 回應與完整來源通報。
- 執行產生的 log 檔不納入 Git；不新增刪除機制。

## 驗證契約

- 單元與整合測試：`python -m pytest tests/test_cli.py tests/test_auto_link_unprocessed_fault_notices.py -q`。
- 回歸測試：`python -m pytest -q`。
- Lint 與差異檢查：`git diff --check`；可用時執行 Ruff。
- E2E：不重跑會變更 MMIS 的正式命令；以離線替身產生並讀取實際 JSONL。
- UI 螢幕截圖：不適用。
- 安全性檢查：檢查 log 允許欄位、Git 忽略規則與 handler 關閉。

## 完成證據

- 變更的檔案：`src/mmis_connector/run_logging.py`、`src/mmis_connector/cli.py`、`src/mmis_connector/auto_link/orchestrator.py`、對應測試、`.gitignore`、`logs/README.md` 與本 Epic 文件。
- 執行過的指令與結果：見 `../verification/MMIS-LOG-001.md`。
- UI 螢幕截圖：不適用。
- 已知限制：零筆紀錄不能推斷 MMIS 歷史狀態；檔案寫入失敗後 stderr 警告但批次照原規則完成；獨立 wheel 安裝的根目錄需另行處理。
- 後續任務：如將來需要 wheel 部署或 log 保留期限，再分別制定任務。
