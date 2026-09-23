# AI-Ready 任務卡

## Metadata

- 任務：實作 HTTP-only 日檢工單明細查詢 CLI
- 上層規格：`ai/artifacts/MMIS HTTP 日檢工單明細查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 日檢工單明細查詢
- 上層 User Story：以工作單號取得故障通報
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002
- 狀態：審查中（實作、驗證與 review 已完成，待人工驗收）
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-23）

## 目標

提供只接受工作單號的 HTTP-only CLI，唯一命中日檢工單後進入明細，解析「故障通報管理」並把可明確判空的 JSON 印到 stdout。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/events.py`、`query_daily_inspection_work_orders.py`、`parser.py`、`cli.py`、`__init__.py`、對應 `tests/`、指定錄製的 HAR／DOM。
- 既有模式：`MMISSession` 單一 session、`MaximoEventClient.load_app/post`、CDATA flatten、動態 table prefix、CLI stdout JSON 與安全錯誤封裝。
- 假設：工作單欄為 `C:5`；查詢唯一完全相符後可點擊 `<prefix>_tdrow_[C:5]_ttxt-lb[R:0]`；click event 的 XML 回應直接包含完整「故障通報管理」表格。HAR 已確認該 click 回應為 HTTP 200 且同時包含表格名稱與第一筆故障通報。
- 未知事項：尚無真實空表錄製；故障通報超過明細目前顯示頁容量的案例尚未錄製。
- 允許變更的檔案：新增 `src/mmis_connector/read_daily_inspection_work_order.py` 與對應測試；最小幅度修改 `parser.py`、`cli.py`、`__init__.py`；本 Epic artifacts、看板、必要情境地圖與 MMIS 知識庫。
- 不得觸碰：`.env`、錄製檔案、session evidence、既有功能契約、UI 與無關檔案。

## 需求

- 新增 `DailyInspectionWorkOrderDetailReader`，重用現有 app 載入與 event client，不複製登入／HTTP 邏輯。
- 在任何網路請求前驗證工作單號為 trim 後非空且只含 ASCII 英數與連字號。
- 載入 `ZZ_PMWO1A`、選擇所有記錄、從表頭解析動態 prefix，對 `C:5` 依序送出 `setvalue` 與 `filterrows`。
- 查詢結果必須恰為一筆且「工作單」完全等於輸入；零筆、多筆與不相符皆安全失敗，不得點擊任意列。
- 點擊唯一結果的工作單儲存格並解析 click response 中 `summary="故障通報管理"` 的唯一表格。
- 擴充通用 parser，使其可用 table summary 限定表格，並能區分空表與表格缺失；不得破壞現有 parser 呼叫。
- 一般儲存格遇到 `<br>` 時輸出 `\n`，並維持既有單行值與 checkbox 行為。
- 成功輸出包含 `success`、`query_name`、`work_order`、`has_fault_notices`、`count`、`records`；空表為成功且固定輸出 false／0／空陣列。
- 新增 `query-daily-inspection-work-order-by-number <工作單號>` CLI；stdout 只印 JSON，不寫入檔案。
- 公開匯出新 reader 類別，維持既有公開 API。

## 驗收標準

- 符合已核准 feature spec 全部驗收標準。
- 指定錄製 DOM 可離線解析 6 筆、四個指定欄位及完整多行故障現象。
- 空表、表格缺失、零命中、多命中、不相符與無效輸入皆有針對性測試。
- 既有兩個 CLI 與 parser 測試維持通過。
- 不新增瀏覽器依賴、敏感 fixture 或檔案輸出行為。

## 實作備註

- 新 reader 可重用 `DailyInspectionWorkOrderQuery._load_app/_post_event` 的行為，但不得透過呼叫原查詢 `run(vehicle, date)` 繞路；若抽共用 private helper 會擴大既有模組風險，優先直接重用 `MaximoEventClient` 的小型編排。
- 日檢清單表頭至少要求「工作單」；為避免誤認其他表格，連同既有日檢欄位集合定位 schema。
- 通用 parser 以目標 `<table summary>` 祖先限制 header 與 row 搜尋；表格存在且無資料列回傳空陣列，目標表格不存在或表頭不完整則拋錯。
- `_cell_value` 對非 checkbox 節點以 `get_text("\n", strip=True)` 擷取顯示內容，並把 title 中的 `<br/>` 標記正規化；測試鎖定單行行為不回歸。
- 本卡不實作明細表分頁；若回應顯示總數超過已解析列數或啟用下一頁控制，必須 fail closed，另立後續卡處理。

## 驗證契約

- 單元測試：輸入驗證、event target／順序、零／多／不相符保護、click target、結果契約、空表、缺表、多行文字、CLI dispatch、公開匯出。
- 整合測試：唯讀解析指定外部錄製 DOM 的 6 筆資料；不複製 HAR／DOM。
- E2E 測試：本機 MMIS 與 `.env` 可用時執行已知工作單 live CLI；不可用時明列殘留風險。
- 型別檢查：不適用（專案未設定 type checker）。
- Lint：不適用（專案未設定 linter）；執行 `python -m compileall -q src tests` 與 `git diff --check`。
- Build：`python -m pip check`。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：搜尋 Playwright／Selenium 與敏感值；審查輸入、同源網路、auth、錯誤輸出、資料不完整 fail-closed。

## 完成證據

- 變更的檔案：`query_daily_inspection_work_orders.py`、`read_daily_inspection_work_order.py`、`parser.py`、`cli.py`、`__init__.py`、`README.md`、對應 tests、context maps 與本 Epic 治理 artifacts。
- 執行過的指令：針對性與完整 `pytest`、`compileall`、`pip check`、`git diff --check`、安全字樣掃描、新舊兩個 live CLI。
- 測試輸出：53 passed、2 skipped；新 live CLI 成功擷取 6 筆且多行換行正確；既有日檢 live 查詢成功回歸。
- 螢幕截圖：不適用。
- 已知限制：尚無真實空表與多頁明細錄製；遇到未完整分頁會 fail closed。
- 後續任務：若 live 證據出現明細分頁，另建立完整分頁擷取任務。
