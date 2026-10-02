# 驗證報告

## 摘要

- 任務：MMIS-023 勾稽後指定故障通報確認誤判
- 結果：離線驗證通過；線上新版寫入待人工驗收
- 驗證者：Codex（2026-10-02）

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_link_fault_notice_to_daily_inspection_work_order.py tests/test_read_daily_inspection_work_order.py tests/test_auto_link_unprocessed_fault_notices.py -q` | 通過 | 含新錄製 DOM 與寫入後重讀測試；既有缺席的 2026-09-24 fixture 測試略過 |
| `python -m pytest -q` | 通過 | 全套離線測試；6 個可選錄製 fixture 測試略過 |
| `python -m compileall -q src tests` | 通過 | 無錯誤輸出 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 只有工作樹換行格式警告 |
| 解析 2026-10-02 Recorder 的 `raw.har` 中工單明細回應 | 通過 | 表格取得 `1150929-07`、`1150929-10`；未保存或輸出敏感 header/token |

## UI 證據

無 UI 變更。錄製 DOM 中同一工單的「故障通報管理」兩列，通報號由 readonly `<input value>` 呈現；修正前解析為兩個空字串，修正後與人工看到的兩筆相符。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 原解析器未讀取資料列 input 的 value | 高 | 已修正並加回歸測試 |
| 寫入後只依即時回應判斷結果 | 中 | 改為重新開啟精確工作單查詢 |
| 原有兩列 SQLite `link_error` 已由使用者人工確認成功 | 中 | 保持原始歷史狀態，不在本卡更改 |

## 殘留風險

- 沒有對 MMIS 執行新版線上寫入；最終端到端行為需下次實際執行驗收。
- 重新查詢若遇到短暫 MMIS 錯誤，仍會安全地報告無法確認，且不自動重送寫入。
