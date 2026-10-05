# 驗證報告

## 摘要

- 任務：MMIS-030 擴充既有臨時檢修查詢的基本資料與 JSON 層級
- 結果：通過，待人工驗收
- 驗證者：Codex

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q` | 通過 | 13 項測試，含基本資料 HAR／DOM 與重複日期不一致 |
| `python -m pytest -q` | 通過 | 全套測試；既有部分案例依環境跳過 |
| `python -m compileall -q src tools/mmis_development tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 無 whitespace 錯誤 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C1-41264` | 通過 | 最上層車號 `EMU815`、級別 `C1`、兩日期 `2026/10/05`、狀態 `完工待回報`；`維修程序概況.count=1`，紀事列車號 `EMA815` |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C2-41266` | 通過 | 最上層八欄；`維修程序概況.count=3`，三種「其它」補充仍正確 |

## 審查發現

- 工單明細的 `檢修日期`、`完工日期` 各有兩個同名標籤與控制項；解析時要求同欄值一致。
- HAR 明細事件中的日期 `value`、`title` 皆空，以 `dojovalue` 轉換台北日期；DOM 快照的 `title` 有顯示日期。兩種錄製均已測試。
- 最上層 `車組/車號` 是工單基本資料，紀事列的同名欄位是每筆維修對象；C1 即時資料分別為 `EMU815` 與 `EMA815`，不可合併。
- 原最上層 `count`、`records` 移至 `維修程序概況`，下游讀取者需要配合更新路徑。

## 安全性與殘留風險

- 沿用現有 session、輸入驗證、工單唯一性檢查與唯讀事件；沒有寫入 MMIS，也沒有輸出憑證。
- 真實空紀事與多頁紀事仍無錄製；空紀事使用合成結構測試，多頁邏輯沿用 MMIS-029。後續取得實例時由維護者補驗證。
- 無 UI 變更，螢幕截圖不適用。
- `mmis-dev-knowledge` 的 `apiPatterns/maximo-basic-detail-labels-and-visible-date` 已合併此次 HAR／DOM 日期後備與重複欄位的驗證經驗；無條目被棄用。

## 後續任務

- 若有依賴舊版 JSON 最上層 `count` 或 `records` 的呼叫端，改讀 `維修程序概況`。
