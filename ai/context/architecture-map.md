# 架構地圖

狀態：已更新（2026-09-24）。

## 系統總覽

`auth.MMISSession` 負責登入與 page state；`events.MaximoEventClient` 重用同一 Session 送出單一或批次 Maximo event 與切換 app；各功能模組編排查詢或已授權寫入；`parser` 將回應 HTML 轉成 JSON-safe records 或動態控制項；`cli` 只負責參數、設定載入、錯誤封裝與 stdout JSON。

## 邊界

| 邊界 | 負責人 | 輸入 | 輸出 | 風險 |
|---|---|---|---|---|
| 環境變數 | CLI | `.env` | 帳號密碼 | 密鑰洩漏 |
| MMIS HTTPS | auth/功能模組 | 表單、event payload | HTML/XML | 認證、CSRF、內網連線 |
| MMIS 遠端寫入 | link 功能模組 | 工作單號、故障通報號 | 關聯資料、確認回應 | 錯誤關聯、結果不明、不可自動重試 |
| HTML parser | parser | Maximo table HTML | records | DOM 結構漂移 |

## 應遵循的模式

- 使用單一 `requests.Session` 保持 cookie。
- 每次登入解析新 hidden fields，每次頁面解析新 PAGESEQNUM、UISESSIONID、CSRFTOKEN、APPID。
- Maximo event 使用當前 page state、Referer、pageseqnum 與 xhrseqnum。
- app 切換與 event payload 組裝統一重用 `MaximoEventClient`，功能模組只負責事件順序與領域參數。
- 同一 UI 動作包含多個 Maximo event 時，使用單一 `post_events()` 依序送出；所有 Maximo POST 禁止 transport 自動重試。
- Maximo list 的動態 table prefix 應由必要欄名集合解析，不寫死錄製中的 prefix。
- 寫入前需唯一且完全相符的業務鍵；寫入後需以領域資料驗證成功，並區分「結果不明」與後續導覽失敗。
- stdout 僅輸出 JSON；診斷訊息送 stderr。
- 功能模組採 `動作_領域物件.py`；查詢類別採 `<DomainObject>Query`，單筆讀取採 `<DomainObject>DetailReader`。

## 應避免的模式

- 寫死帳密、cookie、token 或 session id。
- 將錄製 HAR 或 session evidence 複製進 repo。
- 使用瀏覽器 fallback。
- 對寫入 POST 自動重試，或只憑 HTTP 200 判定寫入成功。
