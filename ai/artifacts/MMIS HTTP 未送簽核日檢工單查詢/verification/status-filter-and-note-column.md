# 驗證報告

## 摘要

- 任務：擴大工作單狀態篩選並新增空白備註欄。
- 結果：通過。依錄製流程清空配屬段後，線上執行得到 9 筆，工作單號與使用者截圖一致。
- 驗證者：Codex。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_query_daily_inspection_work_orders_not_submitted.py -q` | 通過 | 20 passed，2 skipped。 |
| `python -m pytest tests/test_query_daily_inspection_work_orders_by_vehicle_and_date.py -q` | 通過 | 17 passed，1 skipped。 |
| `python -m compileall -q src/mmis_connector/daily_inspection/not_submitted.py tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py` | 通過 | 無語法錯誤。 |
| `git diff --check` | 通過 | 無 whitespace 錯誤。 |
| SQLite `PRAGMA table_info`、筆數與空白備註查詢 | 通過 | 15 欄；最右欄為備註欄；原有 8 筆仍在，8 筆備註全空白。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval`，原本切「所有記錄」 | 未通過 | 翻頁時 HTTPS 回應 `ReadTimeout`（20 秒）；該次未覆寫快照。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval`，進入 1A 後直接過濾 | 通過但筆數待釐清 | `Status: SUCCESS`、`Records found: 3`；SQLite 備註均空白。 |
| 預設清單十種狀態逐一過濾 | 通過 | 依序為 2、0、0、0、0、0、0、0、1、0 筆，合計 3 筆。 |
| 預設清單只按工作單號過濾 | 通過 | `115-1A-80516` 為 1 筆；截圖中的 `115-1A-80581` 為 0 筆。 |
| 使用者提供的 1A 畫面截圖 | 通過 | 畫面顯示 9 筆，包括 `115-1A-80581`；修正後資料庫的 9 個工作單號與截圖一致。 |
| 錄製檔 `2026-11-03_check-daily-inspection-work-order-maintenance-records-completion` | 通過 | HAR 中依序送出檢修段、清空配屬段、檢修日期、工作單狀態與 `filterrows`；進入 1A 時配屬段預設值為 `=新竹機務段`。錄製當下結果為 10 筆。 |
| 錄製檔最終 DOM 解析 | 通過 | 分頁總數與實際解析列數均為 10，包含 `115-1A-80581`。 |
| 修正前的回歸測試 | 預期失敗 | 缺少對配屬段 `C:2` 的空值 `setvalue`，斷言結果為 `assert False`。 |
| 修正後執行指定 CLI | 通過 | `Status: SUCCESS`、`Records found: 9`。 |
| 直接查詢 SQLite 快照 | 通過 | `integrity_check=ok`、9 筆、15 欄、9 筆備註皆空白；9 個工作單號與使用者截圖完全一致。 |
| 獨立程式碼審查 | 通過 | 查詢流程、相關測試與文件無需修正事項；未新增多餘註解。 |

## 審查發現與殘留風險

- 篩選字串使用既有 Maximo 逗號多值格式，沒有新認證、權限或密鑰處理。
- 快照採既有交易寫入；線上查詢失敗時不執行資料庫重建。
- 1A 頁面帶入配屬段預設值，若未清空會排除畫面中的部分工單。程式已依錄製事件清空該欄，並在當次線上查詢中核對結果。MMIS 資料會變動，9 筆是本次驗證時的快照筆數，不是固定契約。
- 本次沒有 UI 變更，不適用螢幕截圖。
