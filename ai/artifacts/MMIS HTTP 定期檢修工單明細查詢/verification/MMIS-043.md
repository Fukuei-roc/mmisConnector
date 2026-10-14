# MMIS-043 驗證報告

## 摘要

- 任務：定期檢修工單查詢新增六欄基本資料。
- 結果：通過，待人工驗收。
- 驗證者：Codex，2026-10-14。

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_periodic_inspection_work_order_details.py -q` | 通過 | 基本資料合成與錄製 DOM 測試通過；兩個歷史錄製檔缺失而略過。 |
| `python -m pytest -q` | 通過 | 全套測試 exit 0；部分依賴外部錄製或即時環境的測試略過。 |
| `python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development/query_periodic_inspection_work_order_details.py tests/test_periodic_inspection_work_order_details.py` | 通過 | exit 0。 |
| `git diff --check` | 通過 | 無空白錯誤；Git 提示工作目錄 LF 將轉為 CRLF。 |
| `python -m tools.mmis_development.query_periodic_inspection_work_order_details 115-2A-69254-001` | 通過 | exit 0；`success=true`，六個第一層欄位依序位於 `維修程序概況` 前，沒有 `基本資料` 物件。 |
| `python -c "import json,pathlib; ..."` | 通過 | 看板 Epic 與卡片 JSON 可解析。 |

## 錄製與即時資料核對

- 錄製 DOM：`2026-10-14_query-periodic-inspection-work-order-basic-information/dom/2026-10-14T055015-893.html`；敏感錄製檔只在本機讀取，未複製進專案。
- 六欄即時輸出：工作單 `115-2A-69254-001`、車組/車號 `EMU931`、檢修級別 `2A`、檢修日期 `2026/09/16`、完工日期 `2026/09/16`、工作單狀態 `工單結案`。
- 使用者修正後重新執行目標測試、全套測試與指定工單即時查詢；六欄直接位於 JSON 第一層。
- 原 `維修程序概況`、`檢修記錄` 與 `維修情形` 仍可在同一次即時查詢中取得。
- CLI 無 UI 變更，無螢幕截圖需求。

## 審查與殘留風險

- 架構：沿用既有 HTTP reader、MMIS session 與標籤定位；未增加請求或瀏覽器依賴。
- 安全：只讀查詢；未儲存憑證、cookie、token 或 HAR。
- 正確性：對工作單一致性、缺欄與衝突欄位拒絕輸出成功結果；日期按既有時區模式解析。
- 殘留風險：僅指定工單經即時驗證；其他工單的 DOM 差異尚未確認。
- 後續：由使用者驗收第一層欄位與順序。
