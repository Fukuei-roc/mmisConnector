# 驗證報告

## 摘要

- 任務：MMIS-023 查詢日檢檢修記錄中備註非空的資料
- 結果：通過；已按使用者最終要求讓「檢修記錄」只包含 `count` 與 `records`，使用者要求 commit／push
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_daily_inspection_inspection_records.py tests/test_architecture.py -q` | 通過 | 14 個目標／架構測試通過 |
| `python -m pytest tests/test_daily_inspection_inspection_records.py -q` | 通過 | 格式調整後 10 個目標測試通過，含完整結果包裝測試 |
| `python -m pytest -q -ra` | 通過 | 全套無失敗；26 個舊測試因本機缺少各自的外部錄製證據而跳過，本任務的錄製 DOM 測試有執行 |
| `python -m compileall -q src tools/mmis_development tests` | 通過 | 無編譯錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 只有 Windows 行尾轉換提示，無 whitespace 錯誤 |
| `python -m tools.mmis_development.query_daily_inspection_work_order_inspection_records 115-1A-71815` | 通過 | live MMIS 唯讀查詢：`count=1`，三欄與錄製範例相符；stdout 為 JSON |
| `python -m tools.mmis_development.query_daily_inspection_work_order_inspection_records 115-1A-10899` | 通過 | 使用者提供工單的 live 唯讀查詢；最外層為 `success`、`query_name`、`work_order`、`檢修記錄`，後者只有 `count` 與 `records` |
| 無參數執行相同命令 | 預期錯誤 | exit code 1，stdout 為 `success=false` JSON |
| 對新增原始碼與測試搜尋瀏覽器依賴、憑證、token 與固定站點 | 通過 | 無命中 |
| 更新 mmis-dev-knowledge `stableWorkflows` | 通過 | 新增 `daily-inspection-inspection-record-remarks-http`，記錄已驗證的頁簽事件與動態表格解析模式 |

## UI 證據

不適用；無 UI 變更，故無螢幕截圖。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 目標表格 `summary` 含動態工單作業 id | 中 | 已以表頭與動態 prefix 定位，且要求 `summary` 為工作單作業表格 |
| 分頁可能造成部分資料遺失 | 中 | 已檢查總數、起點、列數與下一頁；缺頁會報錯；合成雙頁測試通過 |
| MMIS 登入與事件需存取內網 | 高 | 沿用既有 `MMISSession`、`open_detail()` 與 `MaximoEventClient`；live 讀取通過，無新憑證處理 |
| 錄製資料含 session 與 token | 高 | 僅本機唯讀分析；未納入版本庫、fixture 或輸出 |
| 成功輸出格式改變 | 低 | 只調整 development tool 的 JSON 包裝；reader 的資料契約與共用錯誤格式維持不變，最終欄位位置已以單元與 live 查詢驗證 |

## 殘留風險

- 只有錄製的單頁 26 筆與合成雙頁案例；尚無 live 空表或 live 多頁案例。若 MMIS 在這些情境的回應形態不同，程式會回報解析錯誤，需要取得新錄製證據後調整。
- 此工具使用 MMIS 登入帳號的既有讀取權限；權限不足時會依現有客戶端錯誤路徑回報。

## 完成定義

實作、目標測試、全套回歸、live 唯讀驗證、編譯、安全檢查與殘留風險均已記錄；使用者確認最終格式並要求 commit／push。
