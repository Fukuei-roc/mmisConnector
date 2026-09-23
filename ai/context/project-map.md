# 專案地圖

狀態：已更新（2026-09-21）。

在專案導入（intake）時填寫這份文件。

## 產品

- 名稱：MMIS Connector
- 使用者：需要以命令列取得 MMIS 未處理故障通報的內部使用者
- 核心工作流程：讀取環境變數 → HTTP 登入 → 重用 Session → 切換故障通報管理 → 套用儲存查詢 → 輸出 JSON

## 技術棧

- 前端：無（CLI）
- 後端：Python 3.11、requests、Beautiful Soup
- 資料庫：無
- 身分驗證：MMIS 表單登入，憑證由 `.env` 載入，登入狀態只保留於程序內的 `requests.Session`
- 測試：pytest、錄製 DOM fixture
- 部署：Windows 本機 CLI

## 重要目錄

| 路徑 | 用途 | 備註 |
|---|---|---|
| `src/mmis_connector/` | HTTP client、工作流程與 CLI | 不得依賴瀏覽器 |
| `tests/` | 單元與錄製證據解析測試 | 不存放敏感 HAR |
| `ai/artifacts/` | 規格、任務卡、驗證證據 | 不記錄憑證或 token |

## 常用指令

| 指令 | 用途 | 備註 |
|---|---|---|
| `python -m mmis_connector query-unprocessed-fault-notices` | 查詢本段未處理通報並輸出 JSON | 需先設定 `.env` |
| `python -m pytest` | 執行測試 | 不連線 MMIS 的測試為預設 |
