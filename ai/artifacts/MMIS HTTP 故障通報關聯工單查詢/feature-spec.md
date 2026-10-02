# 功能規格書

## Metadata

- 功能：HTTP 查詢故障通報關聯的工單
- 負責人：Codex
- 狀態：使用者已明確要求，已實作
- 風險等級：高（既有認證及內部網路唯讀存取）

## 問題與目標

輸入通報號後，在命令列取得「檢視所有段檢修工單」的完整資料，不啟動瀏覽器或產生查詢結果檔。

## 非目標

- 不建立或修改 MMIS 工單、勾稽關係或故障通報。
- 不加入正式 `mmis-connector` CLI。
- 不保存錄製 HAR、session、查詢結果。

## 使用者故事與驗收標準

| 故事 | 驗收標準 |
|---|---|
| 依通報號查工單 | `python -m tools.mmis_development.query_work_orders_linked_to_fault_notice 1150910-14` 輸出成功 JSON，包含三張指定工作單與七個指定欄位 |
| 消除重複顯示 | 按工作單去重，維持首次出現順序；`count` 是去重後筆數 |
| 取得完整清單 | 依目標表格分頁讀取至總筆數；空表輸出 `[]`；範圍或回應異常則失敗 |

## 資料與 API

- 輸入：一個符合 `7 位數字-2 位數字` 的通報號。
- 輸出：stdout JSON，包含 `success`、`query_name`、`fault_notice`、`count`、`records`。每筆 record 包含工作單、工單級別、車組/車號、工作單說明、工作單狀態、通報號、狀態。
- 併單時工單列的「通報號」可能是主通報號，與輸入通報號不同；保留表格原值。
- 錯誤：非零退出碼與 JSON 錯誤物件；不輸出部分成功資料。
- 身分驗證：重用 `.env`、`MMISSession` 與既有 Maximo event client；僅送出查詢及頁籤 click event。

## 驗證計畫

- 錄製 DOM、去重、跨頁、空表、分頁失敗路徑測試。
- 完整 pytest、compileall、diff check 與一次唯讀 live 查詢。
- 無 UI 變更，螢幕截圖不適用。
