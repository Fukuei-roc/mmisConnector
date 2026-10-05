# 驗證報告

## 摘要

- 任務：MMIS-032 臨時檢修工單查詢速度優化
- 結果：通過，待人工驗收
- 驗證者：Codex

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q` | 通過 | 19 項測試，含預設清單命中、零筆回退、兩輪零筆、首輪分頁異常拒絕回退，以及原 JSON 回歸 |
| `python -m pytest -q` | 通過 | 全套測試；既有部分案例依本機錄製或環境條件跳過 |
| `python -m compileall -q src tools/mmis_development tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 無 whitespace 錯誤 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C1-41264` | 通過 | 預設清單直接命中；輸出 1 筆通報、1 筆紀事；單次執行約 7.7 秒 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C1-36682` | 通過 | 預設清單零筆後回退「所有記錄」；工單狀態為 `工單結案`，輸出 1 筆通報、2 筆紀事 |
| 交錯 A/B 實測 `115-C1-41264`，各 2 次 | 通過 | 由 `HEAD` 載入舊版 reader，與新版共用相同 MMIS client 實作；執行順序為舊→新→新→舊，四次 JSON 相同。舊版總耗時 `13.25`、`10.99` 秒，新版 `7.59`、`6.84` 秒；平均縮短 `4.91` 秒。從 app 載入完成到點開工單前，平均由 `6.27` 降為 `1.85` 秒，縮短 `4.41` 秒 |

## 審查發現

- 錄製 app 載入回應本身已有 `工作單` 表格欄位；`MaximoEventClient.load_app_with_response` 回傳同一次 GET 的 HTML，無額外 GET。既有 `load_app` 回傳型態維持不變。
- 錄製 `115-C1-41264` 預設清單直接命中；`115-C1-36682` 首輪回應 `0 - 0/0`，切所有記錄並重填條件後為 `1 - 1/1`。
- 回退條件只接受表格與計數一致的真實零筆；結果不唯一、與輸入不符或分頁異常直接失敗。
- 交錯 A/B 各只有 2 次樣本，執行時間會受登入、網路與 MMIS 負載影響；平均縮短 `4.91` 秒是本次條件下的實測值，不保證每次固定節省相同秒數。

## 安全性與殘留風險

- 沿用 `normalize_work_order`、`MMISSession`、唯讀查詢事件與工單唯一性驗證，沒有新增寫入、憑證輸出或錄製檔複製。
- 已以 `工單結案` 工單驗證回退；尚無 `工單取消` 實例。兩種狀態皆依零筆回退規則處理，後續若有取消工單號可補即時驗證。
- 無 UI 變更，螢幕截圖不適用。
- `mmis-dev-knowledge` 新增 `stableWorkflows/temporary-repair-filter-default-then-all-records`，並更新查詢指南第 1.1 節，說明通用先切所有記錄原則在 `ZZ_CMWO` 的已驗證例外；未棄用其他條目。

## 後續任務

- 若需量化效能收益，使用同環境多次量測登入後查詢階段的延遲，再比較兩種流程。
