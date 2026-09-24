# AI-Ready 任務卡

## Metadata

- 任務：以車號與日期查詢日檢工單增量調整
- 上層規格：`ai/artifacts/MMIS HTTP 日檢工單查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 日檢工單查詢
- 上層 User Story：依車號與日期查詢日檢工單
- 分軌：後端
- 前置任務（dependsOn）：MMIS-008
- 狀態：審查中（實作、驗證與 review 已完成，待人工驗收）
- 風險等級：高（重用 MMIS 身分驗證並送出內網 HTTP event）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-24 明確要求修改程式、重新命名並更新 README）

## 目標

將程式英文名稱改為 Query Daily Inspection Work Orders by Vehicle and Date，新增固定工作單狀態，並允許使用者在檢修日期輸入 `=`、`>`、`<`、`>=`、`<=` 或省略運算子。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/query_daily_inspection_work_orders_by_vehicle_and_date.py`、`cli.py`、`__init__.py`、`read_daily_inspection_work_order.py`、對應 tests、`README.md`、指定錄製的 summary／workflow／timeline／DOM。
- 既有模式：HTTP-only、單一 `requests.Session`、動態 table prefix、逐一 `setvalue` 後送出 `filterrows`、stdout JSON。
- 假設：重新命名涵蓋 Python 模組與 CLI 子命令；公開 Query 類別與 JSON 欄位結構保持相容；省略日期運算子時把正規化日期原樣交給 MMIS，由系統套用等於語意。
- 未知事項：錄製目錄缺少 README 所述的 `raw.har`；完整 request body 只能由 `workflow.json` 的已處理事件證據交叉確認。
- 允許變更的檔案：上述功能模組、引用端、對應 tests、README、本 Epic artifacts、看板卡與必要的 context maps。
- 不得觸碰：`.env`、外部錄製檔、session evidence、其他 MMIS 功能行為與資料輸出欄位。

## 需求

- 模組重新命名為 `query_daily_inspection_work_orders_by_vehicle_and_date.py`，CLI 重新命名為 `query-daily-inspection-work-orders-by-vehicle-and-date`。
- 固定套用 `工作單狀態=執行中已派工,核簽中`。
- 日期接受無運算子或 `=`、`>`、`<`、`>=`、`<=`；日期本體須為有效 `YYYY/M/D` 或 `YYYY/MM/DD`，送出前補零。
- 查詢事件依錄製順序使用 C1、C8、C11、C3，再送出 `filterrows`。
- JSON 欄位結構、records 解析、零筆訊息與分頁 fail-closed 行為不變。
- README 更新新名稱、參數、固定條件與範例。

## 驗收標準

- 新 CLI 名稱可接收車號與日期條件並呼叫 HTTP-only Query。
- 五種顯式運算子與無運算子日期皆正規化且原樣保留運算子；非法或重複運算子在網路請求前遭拒。
- event 測試證明固定狀態值與錄製順序正確。
- 成功、零筆與分頁保護的 JSON 欄位結構維持原契約。
- 工作單明細 reader 與完整測試套件保持通過。

## 實作備註

- 使用標準函式庫與明確 regex 解析運算子，不新增依賴或抽象層。
- `inspection_date` 輸出仍為不含運算子的正規化日期，保持既有資料契約；完整條件只用於 MMIS event。
- Query 類別名稱保持 `DailyInspectionWorkOrderQuery`，避免無必要的公開 Python API 破壞。

## 驗證契約

- 單元測試：日期運算子、非法輸入、event 值／順序、成功／零筆／分頁、CLI dispatch、public API、detail reader 回歸。
- 整合測試：唯讀解析指定錄製 DOM，並核對 DOM 的 C8 固定狀態與零筆狀態。
- E2E 測試：若本機環境與內網可用，執行新 CLI live 查詢；否則記錄原因與風險。
- 型別檢查：不適用（專案未設定 type checker）。
- Lint：不適用（專案未設定 linter）；執行 `compileall` 與 `git diff --check`。
- Build：`python -m pip check`。
- 螢幕截圖：不適用，無 UI 變更；錄製截圖僅作唯讀參考。
- 安全性檢查：確認無敏感錄製資料、瀏覽器依賴與未驗證網路邊界進入 diff。

## 完成證據

- 變更的檔案：日檢查詢模組改名；更新 `cli.py`、`__init__.py`、明細 reader 引用、對應 tests、`README.md`、context maps、feature spec、任務卡、看板與驗證報告。
- 執行過的指令：針對性 pytest、完整 pytest、`compileall`、`pip check`、`git diff --check`、stale-name／敏感內容掃描、新 CLI live 查詢。
- 測試輸出：完整測試 `65 passed, 2 skipped`；live 查詢 `success=true` 且回傳 1 筆；語法、依賴與 diff 檢查通過。
- 螢幕截圖：不適用。
- 已知限制：指定錄製缺少實體 raw.har；live 僅覆蓋 `>`，其餘允許運算子由單元測試覆蓋；多頁結果維持 fail closed。
- 後續任務：若業務需要多頁日檢結果，再建立分頁擷取任務卡。
