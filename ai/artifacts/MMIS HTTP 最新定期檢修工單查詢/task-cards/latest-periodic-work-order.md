# 最新定期檢修工單查詢任務卡

## Metadata

- 任務：新增車組/車號查詢最新定期檢修工單的 development 指令。
- 上層規格：`ai/artifacts/MMIS HTTP 最新定期檢修工單查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 最新定期檢修工單查詢
- 上層 User Story：最新工單查詢
- 分軌：後端
- 前置任務（dependsOn）：無
- 狀態：完成
- 風險等級：高（MMIS 網路與登入邊界；唯讀）
- Agent owner：Codex
- 人工核准者：使用者於 2026-10-27 直接指定功能、錄製檔及實作驗證。

## 目標與情境包

- 目標：輸入車組/車號後，只列印日期最新的一筆定期檢修工單四欄 JSON。
- 相關檔案：`src/mmis_connector/periodic_inspection/reader.py`、`src/mmis_connector/daily_inspection/query.py`、`src/mmis_connector/events.py`、`src/mmis_connector/parser.py`、`tools/mmis_development/`、`tests/test_architecture.py`、指定錄製。
- 既有模式：MMISSession 登入，MaximoEventClient 切 app 與送 event，parser 依表頭定位動態欄位，run_json_tool 輸出 JSON。
- 假設：錄製中的「檢查室」與「工單結案,簽核中」是本指令的固定查詢範圍；不以清單順序推定日期順序。
- 未知事項：實際 MMIS 的車號文字比對規則及未來表格欄位是否改動。
- 情境預算：讀專案地圖、流程、相關 query/reader/parser/wrapper、錄製摘要與查詢事件、HAR 的目標回應；跳過不相關故障通報與完整靜態資源。
- 允許變更的檔案：新 periodic query、新 development wrapper、對應測試、`tests/test_architecture.py`、`tools/mmis_development/README.md`、本 Epic 產出物。
- 不得觸碰：錄製檔、憑證、`.env`、其他既有查詢行為。

## 契約與驗收

- 入口只接受一個非空車組/車號；成功 JSON 僅有車組/車號、檢修級別、工作單、檢修日期。
- 遍歷所有結果頁，驗證計數與日期；同日以工作單號決定唯一結果。
- 查無資料、缺少欄位、日期無效或分頁不一致時，回傳既有 JSON 錯誤與非零結束碼。
- 無資料庫遷移；回滾方式是移除此唯讀指令與查詢模組。

## 驗證契約

- 單元與整合測試：事件順序、跨頁最新值、空結果、日期與分頁錯誤、CLI JSON。
- 完整測試：`python -m pytest -q`。
- 編譯：`python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development/query_latest_periodic_inspection_work_order.py`。
- 差異檢查：`git diff --check`；安全檢查確認沒有 HAR、cookie、token 或帳密進入版本庫。
- 螢幕截圖：不適用，CLI 沒有 UI 變更。錄製截圖僅用於對照欄位。

## 完成證據

- 變更的檔案：`src/mmis_connector/periodic_inspection/query.py`、`tools/mmis_development/query_latest_periodic_inspection_work_order.py`、`tests/test_query_latest_periodic_inspection_work_order.py`、`tests/test_architecture.py`、`tools/mmis_development/README.md` 及本 Epic 產出物。
- 執行過的指令與結果：見 `verification/latest-periodic-work-order.md`。完整測試、編譯、diff 檢查與 `701` 即時唯讀查詢均通過。
- 螢幕截圖：不適用，沒有 UI 變更。
- 已知限制：數字車號在複合標籤中的邊界語意，僅以錄製案例 `EMU701` 及碰撞測試 `EMU1701` 驗證。
- 後續任務：若 MMIS 使用其他複合車號格式，取得對應錄製資料後調整比對規則。
