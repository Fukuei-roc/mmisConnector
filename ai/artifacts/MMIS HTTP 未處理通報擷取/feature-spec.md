# 功能規格書

## Metadata

- 功能：MMIS HTTP 未處理通報擷取
- 負責人：專案使用者
- 狀態：已實作（2026-09-21；2026-09-24 加入雙查詢筆數比較）
- 風險等級：高

## 問題

目前取得「本段未處理通報(車輛配屬段)」依賴人工瀏覽器操作，無法以穩定、可測試的 CLI 流程重用。

## 使用者

需要從 Windows 命令列取得 MMIS 未處理故障通報的授權內部使用者。

## 目標

- 不啟動瀏覽器，以 HTTP 重現錄製流程。
- 將登入/session 與業務操作分成兩個模組。
- 依序比較「未處理故障通報(車輛配屬段)」與「未處理故障通報(開單時所屬段)」總筆數，選擇筆數較多者；平手時優先車輛配屬段。
- 讀取選定查詢的總筆數，依序取得每一頁，並將所有資料列以 UTF-8 JSON 輸出到 stdout。

## 非目標

- 不下載或格式化 Excel。
- 不提供 UI、排程器或跨程序 session 持久化。
- 不支援任意 Maximo app 或任意儲存查詢。
- 不加入 Playwright fallback。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 登入並保持 Session | 身為使用者，我想從 `.env` 登入並在程序內保持狀態，以便後續操作重用認證 | 同一 `requests.Session` 保有 cookies 與最新頁面狀態；失敗回傳安全錯誤 |
| 查詢並輸出故障通報 JSON | 身為使用者，我想套用指定儲存查詢並取得資料，以便由其他工具消費 | stdout 為有效 JSON，含 `success`、`query_name`、`count`、`records` |

## 使用者旅程

```text
設定 .env → 執行 CLI → HTTP 登入 → 載入首頁 → changeapp(ZZ_FNM)
→ 依序套用車輛配屬段與開單時所屬段查詢 → 比較總筆數
→ 選擇筆數較多者（平手選車輛配屬段） → 依序取得選定查詢的所有分頁
→ 合併並驗證所有列 → stdout JSON
```

## 功能需求

- WHEN CLI 啟動，THE SYSTEM SHALL 從 `.env` 讀取 `MMIS_USERNAME` 與 `MMIS_PASSWORD`。
- WHEN 登入成功，THE SYSTEM SHALL 使用同一 Session 執行後續請求。
- WHEN 進入故障通報管理，THE SYSTEM SHALL 依序套用「未處理故障通報(車輛配屬段)」與「未處理故障通報(開單時所屬段)」，並驗證每個回應含指定查詢名稱與結果總筆數。
- WHEN 兩個查詢總筆數不同，THE SYSTEM SHALL 選擇筆數較多的查詢擷取資料。
- WHEN 兩個查詢總筆數相同，THE SYSTEM SHALL 選擇「未處理故障通報(車輛配屬段)」。
- WHEN 結果總筆數超過單頁筆數，THE SYSTEM SHALL 依序送出下一頁事件，直到擷取筆數等於總筆數。
- WHEN 分頁範圍不連續、總筆數改變或無法取得下一頁，THE SYSTEM SHALL 明確失敗，不得輸出不完整結果。
- WHEN 結果包含空值或 checkbox，THE SYSTEM SHALL 分別輸出空字串或 boolean。
- WHEN 發生錯誤，THE SYSTEM SHALL 以非零 exit code 輸出不含敏感值的 JSON 錯誤。

## 畫面

無 UI。

## 資料與 API

- 輸入：`MMIS_USERNAME`、`MMIS_PASSWORD`、可選 `MMIS_BASE_URL`、`MMIS_VERIFY_SSL`、`MMIS_TIMEOUT_SECONDS`。
- 輸出：`{"success": true, "query_name": str, "count": int, "records": object[]}`。
- 欄位：車次、車組/車號、發生日期、發生時間、事故等級、故障地點、ATP故障、故障現象、立案人員、通報人員、通報單位、通報股室、狀態、通報號、配屬段別、配屬段別名稱、顏色查詢。
- 驗證：結果筆數須等於解析到的資料列數；表頭或列結構不存在時明確失敗。
- 錯誤：credentials、登入 redirect、page state、shared session、query response、network 與 parse errors 統一封裝。

## 安全性與隱私

- `.env`、cookie、CSRF token、session id 不得進入 git 或 stdout。
- 不記錄 request body、response body 或 credentials。
- Base URL 僅接受 HTTPS（測試例外由 dependency injection 處理）。

## 驗收標準

- 程式碼明確分為登入/session 與首頁後工作流程。
- 不安裝、不匯入、不呼叫瀏覽器工具。
- 錄製最終 DOM fixture 可解析出第二頁 2 筆與正確欄位。
- 22 筆錄製 HAR 案例會依序解析第一頁 20 筆與第二頁 2 筆，最後合併為 22 筆。
- 實際執行能輸出當下 MMIS 查詢結果 JSON。
- 兩個查詢皆會被依序檢查；較大者被選定，筆數相同時選定車輛配屬段。
- 選定查詢超過 20 筆時仍會完整擷取所有分頁。
- 輸出物仍為 `success`、`query_name`、`count`、`records`，且 `query_name` 反映實際選定的查詢。

## 驗證計畫

- 單元測試：page state、表格、空值、checkbox、錯誤紅action。
- 整合測試：以 fake Session 驗證登入與 event sequence。
- E2E：經人工核准後對 MMIS 執行一次。
- 視覺：不適用。
- 手動：確認 stdout 可由 `ConvertFrom-Json` 解析且不含敏感欄位。
