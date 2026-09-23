# 驗證報告

## 摘要

- 任務：MMIS-009 實作 HTTP-only 日檢工單明細查詢 CLI
- 結果：通過
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_read_daily_inspection_work_order.py tests/test_query_daily_inspection_work_orders.py tests/test_cli.py tests/test_public_api.py` | 通過 | 35 passed、1 skipped（第一輪修正空清單 fixture 後重跑） |
| `python -m pytest` | 通過 | 53 passed、2 skipped；跳過項目皆為本機未提供的舊外部錄製 DOM，不屬於本功能；本功能指定 DOM 測試有執行並通過 |
| `python -m compileall -q src tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 僅有 Git 的 LF→CRLF 工作目錄提示，無 whitespace error |
| live `query-daily-inspection-work-order-by-number 115-1A-70048` | 通過 | exit 0、success true、6 筆、`has_fault_notices=true`、第一筆故障現象含換行、四個欄位完整 |
| live `query-daily-inspection-work-orders 703 2026/09/22` | 通過 | 既有指令回歸：exit 0、success true、1 筆 |
| `rg` 瀏覽器依賴掃描 | 通過 | `src`／`tests` 無 Playwright、Selenium、WebDriver |
| `rg` 敏感詞掃描與人工核對 | 通過 | 僅命中既有 auth/event 動態欄位與假測試值；新程式未加入真實帳密、token、cookie 或 session id |
| MMIS 共用知識庫更新 | 通過 | `apiPatterns/maximo-list-row-click-can-return-detail-view` 已新增，未取代或 deprecated 既有項目 |
| `git diff --check -- README.md` | 通過 | 新增功能表、操作方式、JSON 契約、架構、測試、錯誤與限制說明；無 whitespace error |

## UI 證據

| Viewport | 螢幕截圖 | 備註 |
|---|---|---|
| 不適用 | 不適用 | 本功能無 UI 變更，只提供 CLI 與 stdout JSON |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 初版測試 helper 以 truthy fallback 將空工作單清單換成預設命中資料 | 中 | 已修正為只在 `None` 時使用預設值；零命中測試現已實際覆蓋錯誤路徑 |
| 全域多行正規化可能改變既有 parser 公開行為 | 中 | 已改為 `normalize_line_breaks=True` 顯式選項，只有新明細 reader 啟用，並新增 opt-in 回歸測試 |
| 未發現未解決的功能、安全、隱私或架構問題 | 無 | 通過 |

## 安全性與可維護性審查

- 發現的問題：無未解決問題。
- 輸入驗證：工作單號在網路事件前 trim，且限制為 ASCII 英數開頭及英數／連字號。
- 身分驗證／權限：完整重用 `MMISSession` 與登入帳號既有權限，未新增認證邊界。
- 網路：完整重用同源 HTTPS、timeout、CSRF 與 Maximo page state；未接受外部 URL。
- 注入／檔案：輸入只作為 JSON event value；無 shell、HTML、SQL 或檔案路徑拼接，且不寫入結果檔。
- 隱私：stdout 僅輸出規格要求的業務資料；錯誤沿用安全封裝，不輸出完整 response 或 session 資訊。
- 正確性：查詢零筆、多筆、不完全相符、明細缺表與未完整分頁均 fail closed；空的目標表格則為明確成功結果。
- 可維護性：日檢 app／所有記錄流程由現有 query 提供共用方法；event、登入與 parser 均重用既有模組。
- 核准建議：核准，進入人工驗收。

## 殘留風險

- 尚無 MMIS 真實「故障通報管理為空」錄製；空表行為以保留目標 table／表頭但零資料列的 DOM fixture 驗證。
- 尚無超過 10 筆的明細錄製；目前偵測到總筆數大於已解析列或啟用下一頁時會安全拒絕，不會輸出不完整資料。
- Maximo UI 若變更 `C:5`、table summary、表頭或 event target 規則，需要同步維護 parser／workflow。
