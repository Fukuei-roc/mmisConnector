# 限定最新定期檢修工單的檢修級別

## Metadata

- 任務：在最新定期檢修工單指令新增 `2A,3A` 檢修級別條件。
- 上層規格：`ai/artifacts/MMIS HTTP 最新定期檢修工單查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 最新定期檢修工單查詢
- 上層 User Story：最新工單查詢
- 分軌：後端
- 前置任務（dependsOn）：原查詢任務已完成。
- 狀態：完成
- 風險等級：高（沿用 MMIS 登入與網路邊界，唯讀）
- Agent owner：Codex
- 人工核准者：使用者於 2026-10-27 明確指定四項條件並要求實作與驗證。

## 目標與情境包

- 目標：輸入 `813` 時只從 `2A`、`3A` 工單選最新一筆，仍列印四欄 JSON。
- 相關檔案：`periodic_inspection/query.py`、對應測試、`tools/mmis_development/README.md`、指定 Recorder timeline 與 HAR。
- 既有模式：動態表頭定位過濾欄位，依序 `setvalue` 後 `filterrows`，跨頁讀取及日期選擇不變。
- 假設：`2A,3A` 是本指令固定業務範圍，不新增 CLI 參數。
- 未知事項：其他車組可能沒有 `2A/3A` 記錄，沿用既有查無資料 JSON 錯誤。
- 情境預算：讀專案地圖、現有 query、測試、README、錄製摘要與目標事件；跳過登入、靜態資源和其他 MMIS 功能。
- 允許變更的檔案：`src/mmis_connector/periodic_inspection/query.py`、`tests/test_query_latest_periodic_inspection_work_order.py`、`tools/mmis_development/README.md`、本 Epic 功能規格、架構規劃、任務卡及驗證報告。
- 不得觸碰：錄製檔、密鑰、其他查詢功能、正式 CLI。

## 契約與驗收

- 四個過濾條件依序為車組/車號、檢修級別 `2A,3A`、檢修單位 `檢查室`、工作單狀態 `工單結案,簽核中`。
- 對命中車組的每筆結果確認檢修級別屬於 `2A/3A`，再依檢修日期選最新；其餘輸出與錯誤契約不變。
- `813` 即時結果應為 `EMU813 / 3A / 115-3A-68700-001 / 2026/09/14`，而非現行的 `TR / 115-3A-68700-003 / 2026/09/18`。
- 無資料模型或持久資料變更；回滾為移除新增的級別事件與驗證規則。

## 驗證契約

- 單元測試：四條件事件順序、級別目標欄位、XHR 序號、排除較新的 `TR`、回應混入錯誤級別時失敗。
- 錄製證據：HAR 的 `filterrows` 回應含 19 筆且僅有 `2A/3A`，最新工單與驗收值相符。
- 整合：`python -m tools.mmis_development.query_latest_periodic_inspection_work_order 813`。
- 全套：`python -m pytest -q`；編譯與 `git diff --check`。
- 安全：確認未提交或輸出 HAR、cookie、token、密碼；UI 螢幕截圖不適用。

## 完成證據

- 變更的檔案：`src/mmis_connector/periodic_inspection/query.py`、`tests/test_query_latest_periodic_inspection_work_order.py`、`tools/mmis_development/README.md`，以及本 Epic 的規格、架構、任務與驗證文件。
- 執行過的指令與輸出：見 `verification/inspection-level-filter.md`。13 項目標測試、完整 pytest、編譯、即時 `813` 查詢及差異檢查均通過。
- 螢幕截圖：不適用，沒有 UI 變更。
- 已知限制：MMIS 即時資料可能變更；Recorder HAR 不納入版本庫，缺少本機檔案時相應測試依標記略過。
- 後續任務：若 MMIS 調整級別代碼或篩選欄位，使用新錄製更新測試。
