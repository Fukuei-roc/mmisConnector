# AI-Ready 任務卡

## Metadata

- 任務：實作 HTTP-only 未結案故障通報零參數查詢工具
- 上層規格：`ai/artifacts/MMIS HTTP 未結案故障通報查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 未結案故障通報查詢
- 上層 User Story：查詢未結案故障通報
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002（皆為 done）
- 狀態：完成（2026-09-30）
- 風險等級：高（MMIS 身分驗證與內部網路讀取；唯讀）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-30：「核准並開始實作」）

## 目標

建立 `python -m tools.mmis_development.query_unclosed_fault_notices`，以固定 saved query 與固定 A、B 級／新竹機務段條件擷取所有分頁，僅輸出 stdout JSON。

## 情境包（Context Pack）

- 相關檔案：`fault_notices/query.py`、`events.py`、`parser.py`、development tool support 與對應 tests。
- 既有模式：domain Query、薄 wrapper、單一 HTTP session、動態 schema、`post_events()`、完整分頁 fail closed、JSON stdout。
- 假設：需要的資料為故障通報表格所有欄位與全部分頁；固定條件以 2026-09-30 recording 為準。
- 未知事項：live 權限拒絕與零筆畫面未錄製；沿用既有 auth/parser 錯誤處理。
- 允許變更的檔案：架構筆記所列 runtime、tests、README、context、artifact 與 MMIS-021 kanban metadata。
- 不得觸碰：`.env`、外部 recording、瀏覽器程式、其他命令契約、不相關的 `mmis-post-feature-refactoring-guide.md` 修改。

## 需求

- 新增正式 `UnclosedFaultNoticeQuery`，重用既有故障通報 app、saved query、parser 與 pagination。
- 動態解析 table prefix 及「事故等級」「配屬段別名稱」欄位。
- 依序送出 saved-query、depot `setvalue`、level `setvalue + filterrows`，xhr sequence 連續。
- 固定輸出 `query_name`、`filters`、`count`、`records`，且 `count == len(records)`。
- 零筆為成功；結構或分頁不一致時不得輸出部分成功。
- tool 不接受參數、不建立檔案、不輸出敏感 session state。
- 保持既有公開 API 與功能行為；新增公開 Query export。

## 驗收標準

- 動態 prefix 測試可使用非錄製 prefix 並產生正確 target。
- 事件順序與 xhr sequence 符合錄製，最後篩選以單一 POST 包含 level `setvalue` 後接 `filterrows`。
- 零筆、單頁、31 筆兩頁、分頁不連續、total 改變、缺 next、查詢名稱缺失及 schema 缺失均有驗證。
- 額外參數在載入 config／網路前失敗。
- stdout 為單一 JSON，無檔案副作用與瀏覽器依賴。
- 完整回歸、安全性與架構邊界檢查通過；一次唯讀 live 驗證成功或明確記錄外部阻礙。

## 實作備註

- 將 app／saved-query／pagination 共用行為放在同檔私有基底，避免新 Query 依賴另一個具體 Query。
- 由 `MaximoTableSchema.headers` 反查唯一欄位編號，再組成 filter target；duplicate／missing header fail closed。
- 分頁從 filter request 後的下一個 xhr sequence 開始。
- Recording 僅由 optional test 在本機只讀；不可複製到 fixture。

## 驗證契約

- 單元測試：Query event sequence、動態 schema、所有分頁與錯誤路徑；development tool 參數／成功 JSON。
- 整合測試：fake session／response 完整流程；optional recorded DOM parser test。
- E2E 測試：所有離線檢查通過後執行一次唯讀命令。
- 型別檢查：未設定專用工具；以 annotations 與 compileall 代替。
- Lint：未設定專用工具；執行 compileall 與 diff check。
- Build：`python -m pip check`。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：敏感字串、錄製檔、檔案寫入、瀏覽器依賴、production→tools import 與 POST retry 邊界。

## 完成證據

- 變更的檔案：新增 `UnclosedFaultNoticeQuery`、零參數 development tool、專屬測試與驗證報告；更新 public API、architecture test、README、project maps 與 governance metadata。
- 執行過的指令：針對性 pytest、完整 `python -m pytest -rs`、compileall、pip check、diff check、安全／依賴掃描、錄製 HAR 形狀檢查及兩次唯讀 live 命令（第一次安全失敗後修正過度驗證；第二次成功）。
- 測試輸出：138 passed、4 skipped；compileall 無輸出（成功）；pip check 無 broken requirements；live exit code 0、count 31、records 31、17 欄位。
- 螢幕截圖：不適用。
- 已知限制：依賴 MMIS 既有 saved-query 名稱、三個必要表頭與 Maximo list event／pagination 結構；四個不屬於本功能的舊 recording tests 因各自本機 fixture 缺失而 skip。
- 後續任務：無必要後續；固定 depot／level 若未來要參數化需另立規格。

## 審查結果

- 架構：核准；production component 位於既有 fault-notices domain，tool 保持薄，production 不依賴 tools。
- 安全性：核准；唯讀、同源 session／CSRF、無秘密輸出、無檔案輸出、無瀏覽器 fallback、POST 無自動重試。
- 測試：核准；動態 target、event sequence、零筆、31 筆分頁、錯誤 schema、錄製 DOM 與 live 均有證據。
- Code review：核准；沒有阻擋或要求修改的發現。
