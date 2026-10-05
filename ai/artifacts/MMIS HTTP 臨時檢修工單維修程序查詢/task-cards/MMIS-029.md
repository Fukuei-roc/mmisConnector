# AI-Ready 任務卡

## Metadata

- 任務：新增臨時檢修工單維修程序概況唯讀查詢工具
- 上層規格：`ai/artifacts/MMIS HTTP 臨時檢修工單維修程序查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 臨時檢修工單維修程序查詢
- 上層 User Story：查詢維修程序
- 分軌：後端
- 前置任務（dependsOn）：無；共用 HTTP session、event、parser 已存在
- 狀態：審查中，待人工驗收
- 風險等級：中
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-05 明確要求新增程式）

## 目標

提供單一工作單號輸入、唯讀查詢全部紀事列、stdout JSON 的 development tool。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/{auth,events,parser}.py`、`daily_inspection/reader.py`、`tools/mmis_development/_support.py`、指定錄製 HAR／DOM。
- 既有模式：一個 `MMISSession`、`MaximoEventClient`、動態表頭定位、唯一業務鍵驗證、安全 JSON CLI。
- 假設：錄製的 `ZZ_CMWO` app、檢修級別 `C1,C2,C3`、檢修回報頁籤仍有效。
- 未知事項：實際空表與多頁清單沒有錄製。
- 允許變更的檔案：新增 `temporary_repair` domain、development wrapper、對應測試與本 Epic artifacts；最小幅度更新工具 README、project map。
- 不得觸碰：`.env`、錄製檔、既有使用者 README 改動、無關功能。
- 情境預算備註：只讀取必要流程、既有 reader／parser、錄製關鍵事件與目標表；未展開完整 HAR 靜態資源。

## 需求與驗收標準

- 執行功能規格的全部資料契約。
- 以「更換數量」表頭辨識正確紀事清單，排除錄製中同名但標頭為「數量」的清單。
- 「其它問題」的紀事列須取該列明細的「其它故障現象」 textarea，以 `其它問題：補充文字` 輸出；多列時切換至正確列。
- 「其它原因」與「其它」的紀事列分別取「其它故障原因」與「其它處置措施」textarea；同列多個其它選項須一次選列後完整補上三欄。
- 選列回應未包含 textarea 時，確認目標列已成為 currentrow 後沿用已渲染的欄位值；空字串保留 `其它問題`。
- 驗證分頁範圍與總筆數，連續讀完全部頁面。
- 不保存查詢檔案或登入資訊。

## 實作備註

- 重用現有 `parse_maximo_table`、`parse_maximo_page_info`、`parse_labeled_inputs`。
- 前端、資料模型與遷移皆不適用。回滾為移除新工具與 domain 模組。

## 驗證契約

- 單元測試：錯誤參數、表格識別、錄製事件與九欄內容。
- 整合測試：指定 HAR 離線解析。
- E2E 測試：本機 `.env` 與網路允許時，執行已知工作單。
- 型別檢查／Lint／Build：`compileall`、`pip check`、`git diff --check`。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：檢查唯讀事件、輸入驗證、敏感資訊、完整性驗證。

## 完成證據

見 `verification/MMIS-029.md`。
