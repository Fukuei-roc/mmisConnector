# AI-Ready 任務卡

## Metadata

- 任務：MMIS-023 依工作單號查詢有備註的日檢檢修記錄
- 上層規格：`ai/artifacts/MMIS HTTP 日檢檢修記錄查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 日檢檢修記錄查詢
- 上層 User Story：查詢有備註的檢修記錄；判斷無備註結果
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002（均 done）
- 狀態：完成；使用者於 2026-10-07 確認最終格式並要求 commit／push
- 風險等級：高（既有身分驗證與內網 HTTP event，唯讀）
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標

新增單一 development tool，以工單號輸出備註非空的日檢檢修記錄 JSON。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/daily_inspection/reader.py`、`parser.py`、`tools/mmis_development/`、`tests/`、指定錄製 HAR 與 DOM。
- 既有模式：重用 `open_detail()`、`parse_maximo_tab_target()`、`parse_maximo_table()`、`parse_maximo_page_info()` 與 `run_json_tool()`。
- 假設：備註 trim 後非空才輸出；錄製的 26 筆只作驗證樣本，不作固定筆數。
- 未知事項：其他工單的實際分頁形態；對分頁不完整採安全錯誤。
- 允許變更的檔案：日檢 reader、對應 development tool、對應 tests、本 Epic artifacts、看板、必要的知識庫與搜尋指南。
- 不得觸碰：`.env`、外部錄製、session evidence、無關 UI 或功能。

## 需求

- 以動態 tab id 點選「檢修回報」與「檢修記錄」。
- 解析唯一目標表格，完整讀取所有資料列；只輸出備註非空的三個欄位。
- 空結果成功；查無工單、表格缺失及分頁不完整失敗。
- stdout 只輸出 JSON，不生成檔案。
- 使用者後續確認的輸出調整：最外層保留 `success`、`query_name`、`work_order`；「檢修記錄」只包含 `count` 與 `records`；錯誤維持共用 CLI 格式。

## 驗收標準

- 錄製 DOM 解析 26 筆，篩選後 1 筆且內容符合規格範例。
- 多筆與全部空白的情況正確；動態 prefix、空白及輸入值欄位正確。
- 不影響既有日檢查詢／勾稽程式。
- 成功 JSON 的「檢修記錄」只含 `count` 與 `records`，為後續同層項目保留結構。

## 實作備註

- 架構：在日檢 domain reader 新增專責類別；現有 detail reader 保持故障通報契約。CLI 採薄 wrapper。
- API：輸入單一工單號；輸出 `success/query_name/work_order/count/records`；無資料庫變更。
- 安全性：重用 `MMISSession` 同源、timeout、憑證與事件封裝；錯誤不包含原始回應或 session 值。
- 回滾：移除本任務新類別、tool 與測試，不影響既有 reader。
- 審查關卡：架構、安全性、測試與 code review。

## 驗證契約

- 單元測試：tab 順序、欄位、空白備註、多筆、零筆、分頁不完整與錯誤。
- 整合測試：本機錄製 DOM 唯讀解析。
- E2E：有效本機 MMIS 憑證與連線可用時執行 live 查詢。
- 型別檢查：沿用專案現有設定（若無獨立 typecheck，不新增工具）。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tools/mmis_development tests`。
- 螢幕截圖：不適用（無 UI 變更）。
- 安全性檢查：檢查依賴與 diff，確認無錄製敏感資料或瀏覽器依賴。

## 完成證據

- 變更的檔案：`src/mmis_connector/daily_inspection/reader.py`、新 development tool、對應測試、架構盤點測試、必要文件與看板。
- 執行過的指令：詳見 `verification/MMIS-023.md`。
- 測試輸出：目標與完整 pytest 通過；live 指定工作單回傳 1 筆，內容吻合錄製案例。
- 螢幕截圖：不適用，無 UI 變更。
- 已知限制：未取得 live 空表與多頁證據；結構不符時報錯。
- 後續任務：後續其他項目的 JSON 輸出另立任務。
