# 功能規格書

## Metadata

- 功能：查詢故障通報關聯的查修工單
- 負責人：Codex
- 狀態：使用者於 2026-10-02 明確要求，已實作
- 風險等級：高（既有登入與內網唯讀查詢）

## 問題與目標

內部使用者輸入通報號後，需要以 HTTP 取得「查修工單」完整十欄，直接列印 JSON，不啟動瀏覽器或產生結果檔。

## 非目標

- 不新增或修改 MMIS 工單及勾稽。
- 不將開發工具加入正式 CLI。
- 不保存 HAR、登入憑證或查詢結果。

## 使用者故事與驗收標準

| 故事 | 驗收標準 |
|---|---|
| 查詢指定通報 | 參數為 `7 位數字-2 位數字`；只接受唯一且完全相符的通報明細 |
| 取得查修工單 | 從「故障追蹤」頁簽中 `summary=查修工單` 的表格讀取十欄，只輸出工作單中段為 `CA` 的列 |
| 完整與安全輸出 | 跨頁讀取、依工作單去重；空表輸出 `records: []`；空欄保留空字串；異常輸出 JSON 錯誤及非零退出碼 |

## 資料與 API

- 輸入：`python -m tools.mmis_development.query_repair_work_orders_linked_to_fault_notice <通報號>`。
- 輸出：stdout JSON，包含 `success`、`query_name`、`fault_notice`、`count`、`records`；每列為工作單、車次、維修情形、狀態判定、檢修廠段、檢修日期、檢修單位、檢查人員、開單人員、工作單狀態。
- 日期：MMIS 若將 date input 的 `value` 留空但提供 `dojovalue`，以台北時區轉為 `YYYY/MM/DD`。
- 錄製註記中的目標表格實際位於「故障追蹤」，並非需求文字所稱的「故障分析」；以 HAR、DOM、畫面與 live 回應為準。

## 安全性與驗證

- 重用 `.env`、`MMISSession`、`MaximoEventClient`；只送查詢、詳情及頁簽 click，不修改遠端資料。
- 以錄製 DOM 測欄位與日期；以合成多頁測空值、空表、CA 篩選、去重及分頁異常；執行全套 pytest、編譯、diff check 與指定通報唯讀 live 查詢。
