# AI-Ready 任務卡

## Metadata

- 任務：臨時檢修工單 JSON 新增工作單並調整輸出排序
- 上層規格：`ai/artifacts/MMIS HTTP 臨時檢修工單維修程序查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 上層 User Story：依工作單號查詢完整工單明細
- 分軌：後端
- 前置任務（dependsOn）：無
- 狀態：完成；使用者於 2026-10-14 指定欄位與排序並提供錄製資料
- 風險等級：中；沿用既有 MMIS 唯讀 session，調整 JSON 契約
- Agent owner：Codex
- 人工核准者：專案使用者（本次明確需求）

## 目標

於 JSON 前五欄依序輸出 `query_name`、`queried_work_order_number`、`success`、`工作單`、`車組/車號`，後續欄位順序不變。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/temporary_repair/reader.py`、`tests/test_temporary_repair_procedure.py`、本 Epic 功能規格、2026-10-14 指定錄製的 HAR 與 DOM。
- 既有模式：以 label/for 定位 Maximo 欄位；同一 session 的 detail response 與檢修回報 response 分別提供欄位；stdout 僅 JSON。
- 假設：查詢號碼採現有正規化值；畫面主工單應與查詢號碼完全一致。
- 未知事項：其他 MMIS 頁面版本是否仍將主工單放於檢修回報 response。
- 允許變更的檔案：臨修 reader、對應測試、此 Epic 的規格、任務卡與驗證報告。
- 不得觸碰：認證、共用 transport、其他查詢器、錄製原檔，以及使用者已修改的 `tools/mmis_development/README.md`。
- 情境預算備註：閱讀專案地圖、流程、臨修 reader 與對應測試，以及指定錄製的相關 DOM/HAR 回應；跳過無關 domain。

## 需求與驗收標準

- `work_order` 重新命名為 `queried_work_order_number`，保留正規化後的查詢值。
- 新增 `工作單`，取檢修回報回應中的主工單欄位；與查詢值不一致時回報錯誤。
- 前五個 JSON 鍵順序精確符合目標；其餘欄位及順序不變。
- 父工單欄位與子單欄位同名時，讀取主工單；主工單缺失時安全報錯。
- 不新增 MMIS event 或寫入。

## 實作備註

- 使用既有 label/for 解析方式；檢修回報 response 已由原流程取得。
- 不更動 MMIS 資料模型；回滾可還原此讀取與 JSON 契約變更。

## 驗證契約

- 單元與錄製：`python -m pytest tests/test_temporary_repair_procedure.py -q`。
- 即時：`python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C1-41264`。
- 全套：`python -m pytest -q`、`python -m compileall -q src/mmis_connector/temporary_repair tools/mmis_development tests/test_temporary_repair_procedure.py`、`git diff --check`。
- UI 螢幕截圖：不適用；此任務只有 CLI JSON 輸出。
- 安全性檢查：不保存 HAR、憑證、cookie 或 token；沿用現有唯讀 session。

## 完成證據

見 `verification/MMIS-045.md`。
