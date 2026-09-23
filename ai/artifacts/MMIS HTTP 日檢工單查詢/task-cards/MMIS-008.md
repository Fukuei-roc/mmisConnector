# AI-Ready 任務卡

## Metadata

- 任務：實作 HTTP-only 日檢工單查詢 CLI
- 上層規格：`ai/artifacts/MMIS HTTP 日檢工單查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 日檢工單查詢
- 上層 User Story：依車號與日期查詢日檢工單
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002
- 狀態：審查中（實作、驗證與 review 已完成，待人工驗收）
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-23 指示開始製作程式）

## 目標

提供接受車組／車號與檢修日期參數的 HTTP-only CLI，輸出日檢工單 JSON，並在零筆時顯示「找不到對應工單」。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/auth.py`、`query_unprocessed_fault_notices.py`、`parser.py`、`cli.py`、`__init__.py`、`tests/`、錄製 workflow 的 timeline 與 DOM。
- 既有模式：單一 `requests.Session`、當前 PageState、同源 HTTPS 限制、Maximo event POST、CDATA flatten、stdout JSON。
- 假設：固定檢修段為新竹機務段；日期條件採大於指定日期；錄製事件欄位語義 C1/C3/C11 維持不變，但 table prefix 由回應解析，不寫死。
- 未知事項：錄製目錄缺少 `raw.har`；目前只錄得單頁成功案例，分頁不在本卡範圍。
- 允許變更的檔案：上述 `src/mmis_connector/` 相關模組、新的共用 event／日檢模組、對應 tests、本 Epic artifacts、看板與持久性專案地圖／知識庫（僅有可重用新發現時）。
- 不得觸碰：`.env`、錄製檔、外部 session evidence、無關功能與 UI。

## 需求

- 將既有 Maximo event POST 與 app 切換邏輯抽成共用模組，既有未處理通報查詢改為重用該模組。
- 新增日檢工單查詢類別，依規格送出所有記錄、三個 setvalue 與 filterrows events。
- 新增可重用的 Maximo list table 解析能力，保留既有故障通報公開 parser 行為。
- 新增 CLI 子命令與兩個必填參數。
- 無資料是 exit code 0 的成功結果，並顯示指定訊息。

## 驗收標準

- 符合已核准 feature spec 全部驗收標準。
- 舊查詢沒有 event 邏輯重複，既有測試保持通過。
- 不新增瀏覽器套件或敏感 fixture。

## 實作備註

- 共用 event 層負責組裝安全的 JSON event payload、PageState 更新、shared-session 拒絕偵測與 app redirect。
- 日檢模組從回應表頭解析動態 table prefix，再組出已驗證的 C1/C3/C11 target。
- 日期使用標準函式庫 `datetime.strptime` 驗證與格式化。
- 若結果總數超出當頁或 next control 已啟用，fail closed，避免靜默輸出不完整資料。

## 驗證契約

- 單元測試：日期驗證、event 順序、結果／零筆／分頁拒絕、CLI dispatch、共用 event 回歸。
- 整合測試：離線解析錄製成功 DOM。
- E2E 測試：環境允許時執行 live CLI；不可用時記錄殘留風險。
- 型別檢查：不適用（專案未設定 type checker）。
- Lint：不適用（專案未設定 linter）；執行 `compileall` 與 `git diff --check`。
- Build：`python -m pip check`。
- 螢幕截圖：不適用，無 UI 變更。
- 安全性檢查：搜尋瀏覽器依賴與敏感字樣；審查輸入驗證、同源網路邊界、錯誤訊息。

## 完成證據

- 變更的檔案：`src/mmis_connector/events.py`、`query_daily_inspection_work_orders.py`、`query_unprocessed_fault_notices.py`、`parser.py`、`cli.py`、`__init__.py`、`pyproject.toml`、對應 tests、context maps 與治理 artifacts。
- 執行過的指令：`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`、`git diff --check`、兩次新 CLI live 查詢、一次既有 CLI live 回歸查詢。
- 測試輸出：33 passed、1 skipped；新查詢 live 命中 1 筆；live 空結果回傳「找不到對應工單」；既有未處理通報 live 回傳成功。
- 螢幕截圖：不適用。
- 已知限制：錄製缺少 raw.har；日檢多頁結果會 fail closed；既有一項測試因本機缺少舊錄製 DOM 而跳過。
- 後續任務：若實際需要多頁，再建立完整分頁擷取卡。
