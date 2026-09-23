# 架構地圖

狀態：已更新（2026-09-21）。

## 系統總覽

`auth.MMISSession` 負責登入與 page state；`query_unprocessed_fault_notices.UnprocessedFaultNoticeQuery` 重用同一 Session 送出 Maximo event；`parser` 將回應 HTML 轉成 JSON-safe records；`cli` 只負責設定載入、錯誤封裝與 stdout JSON。

## 邊界

| 邊界 | 負責人 | 輸入 | 輸出 | 風險 |
|---|---|---|---|---|
| 環境變數 | CLI | `.env` | 帳號密碼 | 密鑰洩漏 |
| MMIS HTTPS | auth/功能模組 | 表單、event payload | HTML/XML | 認證、CSRF、內網連線 |
| HTML parser | parser | Maximo table HTML | records | DOM 結構漂移 |

## 應遵循的模式

- 使用單一 `requests.Session` 保持 cookie。
- 每次登入解析新 hidden fields，每次頁面解析新 PAGESEQNUM、UISESSIONID、CSRFTOKEN、APPID。
- Maximo event 使用當前 page state、Referer、pageseqnum 與 xhrseqnum。
- stdout 僅輸出 JSON；診斷訊息送 stderr。
- 功能模組採 `動作_領域物件.py`；查詢類別採 `<DomainObject>Query`，單筆讀取採 `<DomainObject>DetailReader`。

## 應避免的模式

- 寫死帳密、cookie、token 或 session id。
- 將錄製 HAR 或 session evidence 複製進 repo。
- 使用瀏覽器 fallback。
