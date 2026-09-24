# AI-Ready 任務卡

## Metadata

- 任務：比較兩種未處理通報並擷取較多者
- 上層規格：`feature-spec.md`
- 上層 Epic：MMIS HTTP 未處理通報擷取
- 上層 User Story：查詢並輸出故障通報 JSON
- 分軌：後端
- 前置任務（dependsOn）：MMIS-007
- 狀態：待人工驗收
- 風險等級：高（既有認證後內網 Maximo event 流程）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-24 本次明確要求）

## 目標

依序檢查車輛配屬段與開單時所屬段的未處理故障通報總筆數，擷取筆數較多者，平手時優先車輛配屬段。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/query_unprocessed_fault_notices.py`、`tests/test_query_unprocessed_fault_notices.py`、`parser.py`、2026-09-24 錄製的 summary/timeline/DOM
- 既有模式：同一 `MMISSession` 重播 Maximo event；從查詢回應的 `.tCount` 解析總筆數；選定後逐頁選取並驗證連續性
- 假設：兩個 saved query 的故障通報表格 schema 相同；查詢回應會回顯完整查詢名稱
- 未知事項：錄製目錄缺少 `raw.har`，事件值以 `timeline.json` 與 DOM 交叉驗證
- 允許變更的檔案：本查詢模組、對應測試、`README.md`、功能規格、本任務卡、驗證報告、看板卡、MMIS 開發知識庫
- 不得觸碰：登入流程、parser 輸出欄位規則、CLI 命令與 JSON schema、其他查詢模組
- 驗證指令：`python -m pytest tests/test_query_unprocessed_fault_notices.py`、`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`、`git diff --check`
- 情境預算備註：只讀專案地圖、查詢/parser/測試、錄製摘要、關鍵 event 及最終 DOM；未展開靜態資源、登入細節與無關 app 流程

## 需求

- 依序套用車輛配屬段與開單時所屬段 saved query。
- 比較兩者總筆數，選擇較大者；相等時選擇車輛配屬段。
- 若選擇車輛配屬段，必須在檢查第二個查詢後切回第一個，使 server-side list state 與後續分頁一致。
- 只對選定查詢擷取後續分頁，保留原有分頁完整性驗證。
- 輸出鍵與 records 欄位結構不變，`query_name` 為實際選定的查詢。

## 驗收標準

- 事件順序固定為先車輛配屬段、後開單時所屬段。
- 開單時所屬段較多時直接擷取該查詢；車輛配屬段較多或平手時切回並擷取車輛配屬段。
- 零筆平手仍選擇車輛配屬段。
- 選定查詢超過 20 筆時，逐頁事件的 `xhrseqnum` 連續遞增，最終 `count == len(records) == total`。
- 分頁範圍不連續、總數變動、缺少下一頁或查詢未回顯時明確失敗。

## 實作備註

- 以不可變 query definition 集中名稱、menu value 與 focus id，不寫死錄製的動態 table prefix。
- 抽出小型 saved-query 選擇與選定查詢分頁函式，不新增依賴或瀏覽器 fallback。

## 驗證契約

- 單元測試：第一個較多、第二個較多、平手、零筆平手、查詢確認失敗。
- 整合測試：模擬選定查詢 20+2 與三頁回應，驗證 event 順序、target/value/xhr sequence 與合併筆數。
- E2E 測試：若環境憑證可用，執行 live CLI；否則明確記錄未執行。
- 型別檢查：專案未設定獨立 typecheck；以 compileall 覆蓋語法/import。
- Lint：專案未設定 lint 工具。
- Build：`python -m compileall -q src tests`。
- 螢幕截圖：不適用（HTTP-only CLI，無 UI 變更）。
- 安全性檢查：不將錄製中的憑證、session、token 或 response 資料寫入 repo/輸出。

## 完成證據

- 變更的檔案：`query_unprocessed_fault_notices.py`、對應測試、`README.md`、功能規格、本任務卡、驗證報告與看板卡；並依 skill 要求回寫外部 MMIS 開發知識庫。
- 執行過的指令：針對性與完整 pytest、compileall、pip check、git diff --check、live CLI 摘要驗證。
- 測試輸出：針對性 10 passed；完整 56 passed、3 skipped；live 選定車輛配屬段並回傳 14/14 筆。
- 螢幕截圖：不適用。
- 已知限制：錄製目錄缺少 `raw.har`；live 當下為 14 比 14，僅實際驗證平手優先分支，其他大小關係與多頁分支由自動測試覆蓋。
- 後續任務：等待專案使用者人工驗收；無必要程式後續任務。
