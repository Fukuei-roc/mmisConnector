# AI-Ready 任務卡

## Metadata

- 任務：實作 HTTP-only 日檢工單故障通報勾稽 CLI
- 上層規格：`ai/artifacts/MMIS HTTP 日檢工單故障通報勾稽/feature-spec.md`
- 上層 Epic：MMIS HTTP 日檢工單故障通報勾稽
- 上層 User Story：以工作單號勾稽故障通報
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002（皆為 done）
- 狀態：完成（2026-09-24 人工驗收通過）
- 風險等級：高（經認證的 MMIS 遠端資料寫入）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-24 核准 MMIS-012 並指示開始實作）

## 目標

新增 `query-daily-inspection-work-order-by-number-and-link-fault-notice <工作單號> <故障通報號>`，以 HTTP-only 流程唯一命中日檢工單、執行單筆故障通報勾稽、驗證結果、返回清單並輸出穩定 JSON。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/events.py`、`parser.py`、`query_fault_notices_linked_to_daily_inspection_work_order_by_number.py`、`cli.py`、`__init__.py`、新功能模組、對應 tests、`README.md`。
- 既有模式：`requests.Session` HTTP-only 流程、GET-only retry、Maximo event state、XML／CDATA flatten、動態 table schema、唯一工單 fail-closed、stdout JSON。
- 假設：MMIS 自身處理重複勾稽；客戶端每次均送出勾稽事件。錄製中的動態 element ID 不穩定，必須由標籤、按鈕文字及 tab title 解析。
- 未知事項：權限拒絕與重複勾稽的 live 回應未錄製；一律以勾稽後表格是否含完全相符通報號判斷，不依賴未確認的提示文案。
- 允許變更的檔案：上述功能與共用模組、對應 tests、README、project/code maps、本 Epic artifacts、`tools/kanban/cards/MMIS-012.json`。
- 不得觸碰：`.env`、原始錄製檔、其他 MMIS CLI 契約、瀏覽器依賴、一次性授權資料以外的 MMIS 資料。

## 需求

- 在 `MaximoEventClient` 增加同一 POST 送出多個事件的能力；既有單事件 `post()` 對外行為不變並重用新能力。
- 既有工作單明細 reader 抽出可重用的「驗證輸入、切換所有記錄、唯一命中、開啟明細」步驟；既有唯讀 JSON 契約不變。
- 新模組驗證故障通報號，動態解析故障通報輸入框、勾稽按鈕與清單 tab。
- 以單一 POST 依序送出 `setvalue` 與 `click`；不得拆成可重試的獨立寫入，也不得自動重送。
- 不做客戶端重複關聯預查；MMIS 防呆後仍以「故障通報管理」含完全相符的通報號確認成功。
- 勾稽確認後點擊清單 tab，並以日檢工單必要表頭確認返回成功。
- 將「寫入結果不明」與「勾稽已確認但返回清單失敗」包裝成不含敏感資訊且語意不同的錯誤。
- CLI 接受恰好兩個參數，公開新操作類別，README 移除「規劃中／不可執行」文字並補上成功輸出與風險說明。
- 不新增依賴、資料庫、瀏覽器 fallback 或批次循環。

## 驗收標準

- 無效工作單號、無效故障通報號及錯誤參數數量在寫入前失敗。
- 工單零筆、多筆、不完全相符或分頁不一致時不送出勾稽事件。
- 控制項由語意結構唯一解析；缺少或重複匹配時 fail closed，不寫死錄製 ID。
- 寫入 payload 恰含 `setvalue`、`click` 兩個事件且順序正確，使用同一 CSRF/page state。
- MMIS transport 僅重試 GET，Maximo POST 不自動重試。
- 勾稽回應缺少指定故障通報號時不回報成功。
- 清單回應缺少日檢工單必要表頭時，回報「勾稽已確認，但返回清單失敗」。
- 成功輸出符合規格的 `operation_name`、`work_order`、`fault_notice`、`linked`、`returned_to_list` 契約。
- 既有唯讀三個 CLI、public API 與完整測試套件保持通過。
- repo 不包含 HAR、cookie、token、session ID、帳密、完整 MMIS 回應或瀏覽器依賴。
- 所有離線驗證通過後，只對 `115-1A-71002`／`1150923-36` 執行一次 live 驗證，不自動重跑。

## 實作備註

- `events.py`：新增以 `(event_type, target_id, value)` 表示的多事件介面，由 client 在送出前注入目前 CSRF token；既有 `post()` 委派給它，降低回歸風險。
- 既有 reader：新增聚焦且可測試的 `open_detail()`，回傳正規化工作單號與明細回應；`run()` 繼續負責唯讀表格輸出。
- `parser.py`：新增特定且 fail-closed 的控制項解析結果 dataclass／函式；輸入 label 以文字及 `for` 關聯、按鈕以精確文字、清單以 `title="清單"` 的 tab 結構解析。
- 新功能模組：負責故障通報號驗證、勾稽事件、成功表格判斷、返回清單與結果 JSON；不把寫入邏輯放進 CLI。
- 寫入 POST 發生任何 transport／HTTP 例外時，轉為「勾稽結果不明，需人工確認」，保留原例外鏈但不輸出敏感內容。
- 勾稽確認之後的清單事件失敗，錯誤必須明確指出勾稽已確認，避免使用者誤認為未寫入。
- 資料模型／遷移：無本機資料變更；遠端錯誤關聯只能由使用者依 MMIS 人工流程回復。

## 驗證契約

- 單元測試：故障通報號正反例、語意控制項唯一解析、單一 POST 雙事件 payload、唯一工單保護、勾稽成功／未確認／結果不明、返回清單成功／失敗、CLI 兩參數 dispatch、public API。
- 整合測試：以去敏錄製 DOM fixture 或最小等價 fixture 跑完整 fake-session 流程；測試必須在未實作前失敗，且不得連線 MMIS。
- E2E 測試：離線測試全通過後執行一次 `python -m mmis_connector query-daily-inspection-work-order-by-number-and-link-fault-notice 115-1A-71002 1150923-36`；禁止換資料或自動重跑，輸出須去敏記錄。
- 型別檢查：不適用（專案未設定 type checker）；以 Python 3.11 type annotations 與測試覆蓋。
- Lint：不適用（專案未設定 linter）；執行 `python -m compileall -q src tests` 與 `git diff --check`。
- Build：`python -m pip check`。
- 螢幕截圖：不適用，無本專案 UI 變更；live 結果以 JSON 與回應解析證據驗證。
- 安全性檢查：掃描敏感詞、HAR／session evidence、瀏覽器依賴；檢查同源 HTTPS、輸入驗證、POST 無重試及 stdout 不洩漏動態狀態。

## 審查關卡

- 架構審查：核准。重用既有 transport、reader 與 parser；只新增多事件 primitive 與單一領域操作，沒有平行 client 或新依賴。
- 安全性審查：核准。必要控制為輸入驗證、唯一命中、同源 TLS/CSRF、POST 無重試、結果驗證、敏感錯誤遮蔽及限定 live 資料。
- 測試策略審查：核准。離線 failure-path 優先、完整回歸後才做一次 live；不以 live 測試替代單元／整合測試。
- UI 關卡：不適用，無 UI 變更。
- 高風險人工核准：核准（2026-09-24）。

## 完成證據

- 變更的檔案：新增勾稽功能模組與測試；更新 event transport、parser、既有 detail reader、CLI、公開 API、README、context maps、規格、看板與驗證報告。
- 執行過的指令：針對性 pytest、完整 `python -m pytest -rs`、`compileall`、`pip check`、`git diff --check`、錄製 XHR／DOM 結構檢查、唯讀 live 前後查詢、一次性 live 勾稽命令。
- 測試輸出：最終完整測試 `85 passed, 3 skipped`；live 勾稽 exit code 0、`linked=true`、`returned_to_list=true`；事後唯讀查詢確認指定故障通報存在。
- 螢幕截圖：不適用。
- 已知限制：MMIS 權限拒絕的確切 DOM 尚無錄製；三個既有錄製 fixture 測試因本機缺少各自 DOM 而跳過，新勾稽錄製 DOM 測試已通過；遠端錯誤關聯仍需人工回復。
- 後續任務：返回清單後的批次處理另立任務，不納入 MMIS-012。
