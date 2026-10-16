# 功能規格書

## Metadata

- 功能：ATP 故障分析選項 HTTP 遍歷與 JSON 匯出
- 負責人：mmisConnector
- 狀態：使用者以 2026-10-16 任務書核准；已實作
- 風險等級：高（認證、網路、檔案）

## 問題

ATP 故障要因、因子、項目有父子相依，獨立清單無法保證合法組合。

## 使用者

需要建立 ATP 選項資料庫的 MMIS 開發者與後續 AI Agent。

## 目標

- 透過既有 HTTP Session 讀取完整三層選項與分頁。
- 以原子替換方式輸出專案根目錄 UTF-8 JSON。
- 將部分失敗與合法空清單區分。

## 非目標

- AI 分類、推論、自動填報及任何 MMIS 業務資料寫入。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| ATP 選項匯出 | 身為開發者，我想取得階層式選項，以便 AI 只建議合法路徑 | 三層關係、統計、錯誤狀態可由 JSON 驗證 |

## 使用者旅程

```text
輸入已勾選 ATP 的通報號 → 登入並查詢 → 遍歷三層 lookup → 輸出 JSON
```

## 功能需求

- WHEN lookup 有下一頁，THE SYSTEM SHALL 讀完所有頁才處理下一分支。
- WHEN 分支無資料，THE SYSTEM SHALL 保留合法空陣列。
- WHEN 請求失敗，THE SYSTEM SHALL 記錄路徑，標示 partial，保留舊完整檔。

## 畫面

無新 UI。

## 資料與 API

- 輸入：已勾選 ATP 故障的通報號與 `.env` MMIS 憑證。
- 輸出：`atp_fault_analysis_options.json`，含名稱、可用代碼、父子關係、統計、狀態與錯誤。
- 驗證：通報號格式、ATP 勾選、lookup 表頭、列數、頁數與選取列。
- 錯誤：初始查詢失敗不輸出；分支失敗輸出 `.partial.json`。

## 安全性與隱私

- 身分驗證：重用 `MMISSession`，憑證不寫檔。
- 權限：使用者帳號現有 MMIS 讀取權限。
- 敏感資料：輸出不含 Cookie、CSRF token 或通報內容。
- 濫用情境：event 只允許頁籤、lookup、選項列、分頁及取消按鈕。

## 驗收標準

- 實際 HTTP 遍歷完成且 JSON 統計與資料一致。
- 六個已知故障要因由 MMIS 回應確認。
- 無瀏覽器依賴且無儲存 event。

## 驗證計畫

- 單元測試：解析、階層、分頁、空清單、錯誤、原子寫檔及唯讀 allowlist。
- 整合測試：實際 MMIS HTTP 遍歷。
- E2E：CLI 執行並檢查輸出。
- 視覺：不適用。
- 手動：檢查 JSON 名稱與統計。
