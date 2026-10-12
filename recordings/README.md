# 查詢日檢工單明細

英文指令名稱：`query_daily_inspection_work_order_details`。

從專案根目錄執行：

```powershell
python -m tools.mmis_development.query_daily_inspection_work_order_details 115-1A-71815
```

## 輸入

- 唯一參數為日檢工作單號，例如 `115-1A-71815`；只接受英數字與連字號，前後空白會移除。
- 透過既有 `.env` MMIS 設定登入；查詢為唯讀操作，不需輸出檔案路徑。

## 輸出

成功時 exit code 為 0，stdout 為一份 UTF-8 JSON。最外層欄位依序為：

| 欄位 | 內容 |
|---|---|
| `query_name` | 固定為 `查詢日檢工單明細`。 |
| `query_work_order_number` | 正規化後的輸入工作單號。 |
| `success` | `true`。 |
| `工作單`、`車組/車號`、`檢修日期`、`車次`、`工作單狀態`、`開單人姓名`、`開單日期` | 工單基本資料；`工作單` 必須與查詢號碼相符。 |
| `已勾稽故障通報` | `{ "count": 筆數, "records": [...] }`；每筆含 `故障通報號`、`發生日期`、`車組/車號`、`故障現象`。 |
| `檢修記錄` | `{ "count": 筆數, "records": [...] }`；只保留備註非空的列，每筆含 `裝置名稱`、`回報結果`、`備註`。 |
| `重要事項紀錄` | `{ "count": 筆數, "records": [...] }`；每筆含 `車組/車號`、`故障類別`、`故障類別說明`、`故障現象`、`故障原因`、`處置措施`、`材料編號(PA)`、`員工代號`、`人員姓名`。 |
| `檢修人員` | 依序分成 `檢查室（檢查員）`、`檢查室（技術人員）`、`檢車室（檢查員）`、`檢車室（技術人員）` 四組；各組皆為 `{ "count": 筆數, "records": [...] }`，每筆只含 `員工代號`、`姓名`，按姓名排序。 |

清單沒有資料時為 `{ "count": 0, "records": [] }`。查詢失敗或參數不正確時 exit code 為 1，stdout JSON 只有 `success: false`、`error` 與 `message`；不會輸出部分查詢結果。

`recordings/` 在此只放指令說明；MMIS 錄製的 HAR、DOM 與 session 資料保存在專案外，不放進這個 repository。
