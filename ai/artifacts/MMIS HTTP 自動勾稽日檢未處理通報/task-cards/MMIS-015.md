# AI-Ready 任務卡

## Metadata

- 任務：串接自動勾稽 CLI、公開 API 與整體驗證
- 上層規格：`ai/artifacts/MMIS HTTP 自動勾稽日檢未處理通報/feature-spec.md`
- 上層 Epic：MMIS HTTP 自動勾稽日檢未處理通報
- 上層 User Story：以單一命令執行與檢視結果
- 分軌：後端
- 前置任務（dependsOn）：`MMIS-014`
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-24）

## 目標

提供正式 CLI 入口、穩定 JSON 契約、使用說明及完整離線驗證證據。

## 情境包（Context Pack）

- 相關檔案：`cli.py`、`__init__.py`、CLI/public API tests、`README.md`、專案地圖與本 Epic 驗證報告。
- 既有模式：命令 handler 驗證參數、載入 config、建立 client、stdout JSON、例外去敏。
- 假設：命令不接受參數，使用架構計畫的固定 DB 路徑。
- 未知事項：live 批次驗證需要額外人工授權，不屬於本卡預設範圍。
- 允許變更的檔案：上述串接、文件、測試與治理 artifacts。
- 不得觸碰：既有命令名稱與輸出契約、憑證、live MMIS 資料。

## 需求

- 註冊 `auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders`。
- 拒絕多餘參數，建立單一 client/store/orchestrator 並輸出摘要。
- 公開 orchestrator 類別。
- README 說明名稱、命令、資料庫位置、續跑／清除規則及 link_error 不重跑政策。
- 執行完整離線驗證及高風險架構、安全、測試、code review。

## 驗收標準

- CLI 無參數可正確 dispatch；多餘參數在登入前失敗。
- stdout 是可解析 JSON，且沒有逐筆來源或敏感資料。
- 既有 CLI 與 public API 測試全數通過。
- 文件與實際契約一致。
- 驗證報告記錄命令、輸出摘要、跳過 live mutation 的理由與殘留風險。

## 實作備註

- CLI 不承擔領域狀態機。
- 不執行 live 批次勾稽，除非使用者另行提供明確資料範圍與一次性授權。

## 驗證契約

- 單元測試：CLI 參數、dispatch、public API、JSON 摘要。
- 整合測試：完整離線 orchestrator + SQLite + fake MMIS。
- E2E 測試：預設不執行 live mutation並記錄原因。
- 型別檢查：專案未配置。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tests`、`python -m pip check`。
- 螢幕截圖：不適用。
- 安全性檢查：執行專案 checklist 與高風險 review gate。

## 完成證據

- 變更的檔案：`src/mmis_connector/cli.py`、`src/mmis_connector/__init__.py`、`tests/test_cli.py`、`tests/test_public_api.py`、`README.md`、專案地圖與本 Epic 治理 artifacts。
- 執行過的指令：針對性 pytest、完整 pytest、compileall、pip check、diff check。
- 測試輸出：16 項針對性測試通過；完整回歸 107 passed、3 optional fixture skipped；語法、依賴與 diff 檢查通過。
- 螢幕截圖：不適用。
- 已知限制：本次 live 批次 12 筆均無後續日檢工單，故未觸發 mutation；SQLite 內部資料依賴本機權限保護；`link_error` 必須人工確認。
- 後續任務：無。
