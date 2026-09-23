# 功能規格書

## Metadata

- 功能：查詢日檢工單
- 負責人：專案使用者
- 狀態：人工已核准（2026-09-23，使用者指示「好的，請開始製作程式。」）
- 風險等級：高（重用 MMIS 身分驗證並送出內網 HTTP event）

## 問題

使用者目前只能在 MMIS「動力車日檢(1A)」畫面手動切換所有記錄、輸入車組／車號與檢修日期，再按 Enter 查找工單。此流程無法由命令列重複使用，且空結果需要人工判讀。

## 使用者

需要由 Windows 本機命令列查詢 MMIS 日檢工單的內部使用者。

## 目標

- 提供 `query-daily-inspection-work-orders` CLI 子命令。
- 讓使用者在指令中輸入車組／車號與檢修日期。
- 全程使用既有 `requests.Session` 與 Maximo HTTP event，不依賴瀏覽器。
- 查詢有結果時輸出 JSON 工單清單；零筆時明確輸出「找不到對應工單」。

## 非目標

- 不開啟或操控 Playwright、Chrome 或其他瀏覽器。
- 不查詢工單明細或工單勾稽的故障通報。
- 不下載 Excel，也不修改外部檔案。
- 不讓使用者覆寫檢修段；本功能固定使用已錄製驗證的「新竹機務段」。
- 本任務不處理超過單頁的分頁擷取；若實際結果顯示有下一頁，程式須拒絕回傳不完整資料並提示錯誤，另開後續任務處理。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 依車號與日期查詢日檢工單 | 身為內部使用者，我想從命令列輸入車組／車號和檢修日期，以便取得對應的 1A 工單 | 不啟動瀏覽器；輸出符合契約的 JSON；有資料、無資料與無效輸入皆可判定 |

## 使用者旅程

```text
身為 MMIS 內部使用者
我執行 python -m mmis_connector query-daily-inspection-work-orders 703 2026/09/22
系統登入 MMIS、進入動力車日檢(1A)、切換所有記錄並套用條件
有資料時取得工單清單；無資料時看到「找不到對應工單」
```

## 功能需求

- WHEN 使用者提供車組／車號與合法日期，THE SYSTEM SHALL 使用既有 `MMISSession` 登入並重用同一 HTTP session。
- WHEN 載入日檢工單應用程式，THE SYSTEM SHALL 以 HTTP event 切換至 `ZZ_PMWO1A`，不得啟動瀏覽器。
- WHEN 執行查詢，THE SYSTEM SHALL 先選擇「所有記錄」，再設定 `C:1=新竹機務段`、`C:3=車組/車號`、`C:11=>YYYY/MM/DD`，最後送出 `filterrows` event。
- WHEN 日期為 `YYYY/M/D` 或 `YYYY/MM/DD`，THE SYSTEM SHALL 驗證其為真實日曆日期並正規化為 `>YYYY/MM/DD`；不得產生重複的 `>>`。
- WHEN 車組／車號為空白，THE SYSTEM SHALL 在發送網路請求前拒絕執行。
- WHEN 回應含一筆或多筆資料，THE SYSTEM SHALL 解析可見欄名與資料列並輸出 JSON-safe records。
- WHEN 回應顯示「沒有要顯示的列。」，THE SYSTEM SHALL 視為成功的零筆結果，輸出 `count: 0`、空 `records` 與 `message: 找不到對應工單`。
- WHEN 回應缺少預期表頭、應用程式識別或出現未處理分頁，THE SYSTEM SHALL 回傳安全且不含 token、cookie、帳密或完整回應內容的錯誤。
- WHEN CLI 執行完成，THE SYSTEM SHALL 僅在 stdout 輸出 JSON。

## 畫面

不適用；本功能只有 CLI 與 JSON 輸出，不變更 UI。

## 資料與 API

- 輸入：`query-daily-inspection-work-orders <車組/車號> <檢修日期>`。
- 車組／車號：trim 後非空字串，原值作為 MMIS `C:3` 查詢值。
- 檢修日期：`YYYY/M/D` 或 `YYYY/MM/DD`，須為有效日期；送往 MMIS 前正規化為 `>YYYY/MM/DD`。
- 固定條件：`C:1=新竹機務段`。
- 成功輸出：`{"success": true, "query_name": "查詢日檢工單", "vehicle": "...", "inspection_date": "YYYY/MM/DD", "count": N, "records": [...]}`。
- 零筆輸出：成功輸出另含 `"message": "找不到對應工單"`。
- 錯誤輸出：沿用 CLI 的 `success: false`、錯誤型別與安全訊息，exit code 為 1。
- 資料模型變更：無。
- 遷移／回滾：無資料遷移；回滾為移除新子命令、功能模組與對應測試。

## 安全性與隱私

- 身分驗證：沿用 `.env` 與 `MMISSession`，不得新增或記錄憑證。
- 權限：使用登入帳號原有 MMIS 權限，不繞過授權。
- 敏感資料：不得將錄製檔的 cookie、session id、CSRF token、帳密或完整 response 寫入 repo、stdout 或測試 fixture。
- 網路邊界：所有請求沿用 `MMISSession.request` 的 HTTPS 同源限制、timeout 與安全錯誤封裝。
- 輸入只會被 JSON 編碼進 Maximo event，不得拼接為指令、URL 或 HTML。

## 驗收標準

- `python -m mmis_connector query-daily-inspection-work-orders 703 2026/09/22` 能解析兩個參數並呼叫 HTTP-only 查詢模組。
- 查詢事件順序與錄製證據一致：進入 1A、所有記錄、固定檢修段、車組／車號、檢修日期、filterrows。
- 已錄製成功 DOM 可離線解析出 1 筆資料，且工作單為對應的 `115-1A-*` 值。
- 無資料 fixture 回傳 exit code 0，JSON 內含 `count: 0`、`records: []` 與「找不到對應工單」。
- 無效或不存在日期在任何登入／HTTP 呼叫前被拒絕。
- 既有 `query-unprocessed-fault-notices` 行為與測試維持通過。
- 原始碼與測試不含 Playwright／Selenium 依賴，亦不含錄製檔中的敏感值。

## 驗證計畫

- 單元測試：參數與日期驗證、event 順序、成功表格解析、空結果、異常回應、CLI dispatch。
- 整合測試：使用錄製的最終 DOM 做唯讀離線解析；不將錄製檔複製進 repo。
- E2E：若本機 MMIS 網路與有效 `.env` 可用，再以已知條件執行一次 live CLI；未執行時必須列為殘留風險。
- 視覺：不適用。
- 手動：核對 stdout 僅含 JSON，並搜尋原始碼／測試是否意外包含敏感資料或瀏覽器依賴。

## 情境預算備註

- 已讀：專案／架構地圖、既有 auth/query/parser/CLI 與測試、MMIS 開發知識、錄製摘要、關鍵 timeline events、成功 DOM。
- 未讀：與查詢無關的靜態資源與完整 40 萬行 timeline；錄製目錄未提供 README 所述 `raw.har`，因此以 timeline、DOM 與既有已驗證知識交叉確認。
