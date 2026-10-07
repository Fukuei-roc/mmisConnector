# 功能規格書

## Metadata

- 功能：依工作單號查詢日檢工單的檢修記錄備註
- 負責人：專案使用者
- 狀態：人工已核准（2026-10-07，使用者確認並要求開始實作；後續明確指定「檢修記錄」只包含 count 與 records）
- 風險等級：高（使用既有 MMIS 身分驗證與內網 HTTP event；操作唯讀）

## 問題

使用者需逐筆開啟「動力車日檢(1A)」工單、切到「檢修回報」的「檢修記錄」，從所有列中找出備註非空的資料並手動抄錄三個欄位。現有依工作單號查詢程式只擷取「故障通報管理」，沒有這項輸出。

## 使用者

以 Windows 命令列查詢 MMIS 日檢工單的內部使用者。

## 目標

- 接受一個「工作單」號，例如 `115-1A-71815`。
- 擷取目標工單「檢修回報 → 檢修記錄」所有資料列中備註非空的「裝置名稱」、「回報結果」、「備註」。
- 支援零筆與多筆符合條件的結果，只將 JSON 印到 stdout。

## 非目標

- 不修改 MMIS 資料、不下載報表、不建立結果檔案。
- 不擷取備註為空的列或其他頁簽資料。
- 不新增瀏覽器依賴；錄製檔只供唯讀分析，不納入執行時依賴或 repository。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 查詢有備註的檢修記錄 | 身為內部使用者，我想輸入日檢工作單號，以便一次取得所有有備註的裝置記錄 | stdout JSON 的 `records` 依畫面順序包含每筆的三個指定欄位 |
| 判斷無備註結果 | 身為內部使用者，我想在所有備註皆空時收到明確空結果，以便和查詢失敗區分 | 成功 JSON 的 `count` 為 0 且 `records` 為空陣列 |

## 使用者旅程

```text
輸入工作單號 → 登入 MMIS → 唯一且完全相符的 1A 工單 → 檢修回報 → 檢修記錄
→ 讀取完整表格 → 篩選備註非空列 → stdout JSON
```

## 功能需求

- WHEN 輸入工作單號，THE SYSTEM SHALL 在連線前 trim 並沿用現有工作單號字元驗證。
- WHEN 查詢工單，THE SYSTEM SHALL 重用既有 HTTP session、Maximo event 與 `DailyInspectionWorkOrderDetailReader.open_detail()` 的唯一命中驗證。
- WHEN 進入工單，THE SYSTEM SHALL 依錄製流程開啟「檢修回報 → 檢修記錄」，以表格語意與必要表頭辨認資料，不寫死錄製的動態 element prefix。
- WHEN 備註為空字串或僅含空白，THE SYSTEM SHALL 排除該列；其他列依表格順序輸出「裝置名稱」、「回報結果」、「備註」原始顯示文字，去除欄位邊界空白。
- WHEN 所有備註皆空，THE SYSTEM SHALL 回傳成功空結果，而非查詢錯誤。
- WHEN 工單不存在、不唯一、表格或必要欄位缺失、或無法確認已讀取全部分頁，THE SYSTEM SHALL 回傳安全錯誤，不得以不完整資料冒充成功結果。
- WHEN 成功或失敗，THE SYSTEM SHALL 遵循 development tool 的 stdout JSON 契約；不輸出帳密、cookie、token 或完整 HTTP 回應。

## 畫面

不適用；本功能不變更 UI。

## 資料與 API

- 輸入：CLI 單一工作單號參數。
- 建議命令：`python -m tools.mmis_development.query_daily_inspection_work_order_inspection_records 115-1A-71815`。
- 成功輸出：`success`、`query_name`、`work_order` 位於最外層；「檢修記錄」只包含 `count` 與 `records`，供後續新增其他同層項目。

```json
{
  "success": true,
  "query_name": "查詢日檢工單檢修記錄",
  "work_order": "115-1A-71815",
  "檢修記錄": {
    "count": 1,
    "records": [
      {
        "裝置名稱": "牽引馬達及齒輪箱組",
        "回報結果": "異常",
        "備註": "EM9373#4齒輪箱洩漏大，禁用。"
      }
    ]
  }
}
```

- 零筆輸出：最外層 `success: true`，其「檢修記錄」下為 `count: 0`、`records: []`；`count` 是符合「備註非空」的筆數，並非來源表格總列數。
- 錯誤輸出：沿用現有 `run_json_tool` 的最外層 `success: false` JSON 與 exit code 1。
- 資料模型：無資料庫與遷移。

## 安全性與隱私

- 使用現有 `.env`、`MMISSession` 與原有 MMIS 讀取權限。
- HTTP 請求沿用同源、timeout 與 session 狀態處理；不儲存錄製 HAR、DOM 或實際查詢結果。
- 工作單號只作為 event 值，不拼接 shell 指令或檔案路徑。

## 驗收標準

- 錄製案例來源表格為 26 筆，指定有備註的範例列可輸出上述三欄及內容。
- 若有多筆備註非空，全部依畫面順序輸出；若全部為空，輸出 `records: []`。
- 成功 JSON 的「檢修記錄」物件只有 `count` 與 `records`；`success`、`query_name`、`work_order` 位於最外層。
- 只以 stdout 印出有效 UTF-8 JSON，不建立結果檔案。
- 工作單查無、不唯一、表格結構漂移及讀取不完整均回傳錯誤；既有查詢與勾稽功能維持正常。

## 驗證計畫

- 單元測試：欄位解析、空白備註、多筆、空結果、表頭缺失及分頁不完整。
- 錄製證據：唯讀解析指定最終 DOM，核對範例與符合條件的總筆數；HAR 與 timeline 驗證頁簽 event 順序。
- 回歸：執行相關 pytest、完整 pytest、`compileall`、`git diff --check`。
- Live：若本機 MMIS 連線與有效憑證可用，執行指定工作單 CLI 核對 JSON；否則列為殘留風險。

## 情境包（Context Pack）

- 任務：新增日檢工單檢修記錄備註查詢程式。
- 相關檔案：`tools/mmis_development/query_daily_inspection_work_order_by_number.py`、`src/mmis_connector/daily_inspection/reader.py`、`src/mmis_connector/parser.py`、`tests/test_read_daily_inspection_work_order.py`，以及指定錄製的摘要、HAR、timeline、DOM。
- 既有模式：薄的 development tool、單一 HTTP session、共用 Maximo event、動態表格解析、stdout JSON。
- 假設：空白備註以 trim 後判定；`count` 代表輸出筆數；查無工單沿用現有錯誤契約。
- 未知事項：頁簽切換的精確 event payload 與回應組合、超過一頁時的實際分頁 event；須在實作前從 HAR 核實。
- 允許變更的檔案：核准後的日檢 reader／parser、對應 development tool 與測試、本 Epic artifacts 和必要看板紀錄。
- 不得觸碰：`.env`、外部錄製檔、session evidence、無關功能與 UI。
- 驗證指令：`python -m pytest`、`python -m compileall -q src tests`、`git diff --check`，及條件允許時的 live CLI。
- 風險等級：高。
- 情境預算備註：已讀專案與架構地圖、現有日檢 reader／tool、流程文件、知識庫指引及錄製摘要與最終 DOM 的關鍵列；靜態資源與無關 app 流量未讀，HAR 的精確 event 尚待核准後深入驗證。
