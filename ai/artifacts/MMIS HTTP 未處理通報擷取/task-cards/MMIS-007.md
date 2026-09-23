# AI-Ready 任務卡

## Metadata

- 任務：完整擷取未處理通報的所有分頁
- 上層規格：`feature-spec.md`
- 上層 Epic：MMIS HTTP 未處理通報擷取
- 上層 User Story：查詢並輸出故障通報 JSON
- 分軌：後端
- 前置任務（dependsOn）：MMIS-006
- 狀態：完成（2026-09-23）
- 風險等級：高（既有認證後網路事件流程）
- Agent owner：Codex
- 人工核准者：專案使用者（本次明確要求）

## 目標

依 MMIS 回應的總筆數與頁面範圍，逐頁擷取「本段未處理通報」並一次輸出完整資料。

## 情境包（Context Pack）

- 相關檔案：`query_unprocessed_fault_notices.py`、`parser.py`、查詢測試、2026-09-23 多頁錄製 HAR/timeline
- 既有模式：同一 `MMISSession` 重播 Maximo event；解析 CDATA 內表格；每個後續 event 遞增 `xhrseqnum`
- 假設：結果頁維持 `起始 - 結束/總筆數` 計數文字，下一頁事件 target 與該表格前綴相同
- 未知事項：live MMIS 在超過兩頁時是否仍保持相同 page sequence；錄製證據顯示前兩頁保持一致
- 允許變更的檔案：功能規格、任務卡、查詢模組、parser、相關測試、驗證報告、看板卡片、MMIS 開發知識庫
- 不得觸碰：登入流程、CLI 輸出 schema、錄製來源、其他功能模組
- 驗證指令：`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`
- 情境預算備註：只讀專案地圖、查詢/parser/測試與錄製中三個關鍵 event；未展開無關靜態資源與其他 app 流程

## 需求

- 從每頁回應解析目前範圍、總筆數與下一頁 target。
- 第一頁未達總筆數時，以 `click`、`value=true` 依序送出下一頁事件。
- 合併各頁 records，驗證頁面連續、總筆數一致，且最後筆數等於總筆數。
- 空結果與單頁結果維持既有輸出行為。

## 驗收標準

- 22 筆案例送出一次下一頁事件並回傳 22 筆。
- 超過兩頁時持續遞增 `xhrseqnum` 並依序擷取，直到最後一頁。
- 分頁缺頁、總數變動、重複/不連續範圍或擷取筆數不符時安全失敗。
- `count == len(records)`，且 JSON schema 不變。

## 實作備註

- 從 `.tCount` 計數元件與表格前綴推導下一頁 target，不寫死錄製中的動態完整 id。
- 不加入 Playwright 或新依賴。

## 驗證契約

- 單元測試：計數解析、無分頁/最後一頁、缺少計數、無下一頁 target。
- 整合測試：模擬 20+2 與三頁回應，驗證 event target/value/xhr sequence 與合併筆數。
- E2E 測試：若環境憑證可用，執行 live CLI；否則明確記錄未執行。
- 型別檢查：專案未設定獨立 typecheck；以 compileall 覆蓋語法/import。
- Lint：專案未設定 lint 工具。
- Build：`python -m compileall -q src tests`。
- 螢幕截圖：不適用（HTTP-only CLI，無 UI 變更）。
- 安全性檢查：不將錄製中的憑證、session、token 或 response 資料寫入 repo/輸出。

## 完成證據

- 變更的檔案：`query_unprocessed_fault_notices.py`、`parser.py`、相關測試、功能規格、本任務卡、驗證報告與看板卡。
- 執行過的指令：`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`、離線 HAR 分頁解析、live CLI。
- 測試輸出：19 passed；HAR 為 20+2=22；live CLI 為 21 筆、17 欄。
- 螢幕截圖：不適用。
- 已知限制：依賴 MMIS 目前的 `.tCount`、「通報號」表頭與 `tablebtn_next_on.gif` DOM 約定；DOM 若改版會明確失敗。
- 後續任務：無必要後續任務。
