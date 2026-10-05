# AI-Ready 任務卡

## Metadata

- 任務：擴充既有臨時檢修工單查詢的已勾稽故障通報清單
- 上層規格：`ai/artifacts/MMIS HTTP 臨時檢修工單維修程序查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 上層 User Story：查詢維修程序
- 分軌：後端
- 前置任務（dependsOn）：MMIS-030 已實作並推送
- 狀態：審查中，待人工驗收
- 風險等級：中；使用既有 MMIS 唯讀登入與事件，擴充 stdout JSON 契約
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-05 明確要求加入已勾稽故障通報）

## 目標

在既有查詢 JSON 的 `工作單狀態` 與 `維修程序概況` 之間加入 `已勾稽故障通報`。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/temporary_repair/reader.py`、`src/mmis_connector/daily_inspection/reader.py`、`src/mmis_connector/parser.py`、`tests/test_temporary_repair_procedure.py`、基本資料錄製 HAR、工具 README 與本 Epic 文件。
- 既有模式：日檢工單以「故障通報管理」表格摘要與四個必要表頭定位，保留表格所有欄位，核對單頁筆數；臨時檢修明細開啟事件已包含同名表格。
- 風險區域：同一回應有多個表格；終端預設 cp950 顯示會讓中文字看似亂碼，實際 UTF-8 JSON 值正常；分頁結果不可只回傳部分資料。
- 假設：臨時檢修工單的故障通報管理表使用與日檢一致的表頭和單頁計數。
- 未知事項：尚無多頁已勾稽故障通報錄製。
- 允許變更的檔案：既有臨時檢修 reader 與測試、工具 README、本 Epic 規格／任務／驗證、project map。
- 不得觸碰：`.env`、錄製檔、無關的 `Prompt.md`、其他功能程式。
- 情境預算備註：只讀取日檢工單相關 reader／測試、臨時檢修明細錄製事件及既有 parser；未展開 HAR 靜態資源。

## 需求與驗收標準

- 最上層新增 `已勾稽故障通報`，含 `count` 與 `records`，每筆保留 `故障通報號`、`發生日期`、`車組/車號`、`故障現象`、`事故等級`。
- C1 一筆通報與 C2 空清單可解析；JSON 順序符合使用者指定。
- 表格缺失、分頁超過單頁或筆數不一致時輸出錯誤，避免回傳不完整結果。
- 原八個基本欄位與維修程序紀事結果維持正確。

## 實作備註

- 重用日檢 `FAULT_HEADERS`、`FAULT_TABLE_SUMMARY` 與共用 `parse_maximo_table`、`parse_maximo_page_info`。
- 不新增查詢程式、登入流程或 MMIS 寫入動作；只擴充既有工單明細事件的解析。
- 資料模型與遷移不適用。回滾為移除新增欄位與解析函式。

## 驗證契約

- 單元測試：錄製 C1 一筆五欄，分頁不完整拒絕回傳。
- 整合測試：原 C2 錄製空清單與 JSON 鍵順序，原紀事測試回歸。
- E2E 測試：C1 和 C2 即時查詢。
- 型別檢查／Lint／Build：`compileall`、`pip check`、`git diff --check`；專案無獨立型別檢查設定。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：仍只做查詢事件、不記錄憑證與 HAR。

## 完成證據

見 `verification/MMIS-031.md`。
