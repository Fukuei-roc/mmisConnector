# 開單日期補查與重複工單判定架構

## 使用方式

使用者執行 `python -m tools.mmis_development.auto_delete_duplicate_daily_inspection_work_orders`。工具先查詢完整未派工清單並重建 SQLite 快照，再補查重複車組的開單日期，最後標記較舊工單。

## 資料形狀

每列以「工作單」為主鍵，保存車組/車號、預計檢修日、查詢時間、開單日期及執行結果。開單日期在清單查詢時未知，以空字串表示；只有重複車組才補查。

## 模組責任

- 現有 development tool wrapper 擁有整個快照與取消候選流程。
- `DailyInspectionWorkOrderDetailReader.open_detail()` 負責開啟唯一工單。
- `parse_daily_inspection_basic_info()` 驗證工單號並讀取車組/車號與開單日期。
- 不匯入 CLI handler、不使用 subprocess，也不新增 production orchestrator。

## 更新順序與不變條件

1. 以現有 SQLite 交易建立新快照，欄位順序為車組/車號、工作單、預計檢修(進廠)日、查詢時間、開單日期、執行結果。
2. 只挑選非空白且有多張工單的車組，在 DB 寫入交易之外逐筆讀取明細。
3. 每筆明細的工作單與車組/車號都必須吻合快照，開單日期必須符合 `YYYY/MM/DD HH:mm`。
4. 更新成功讀到的日期。只有同組每張工單都有有效日期且最新日期唯一時，才將其他工單標記「待工單取消」。
5. 查詢失敗、欄位不符、日期無效或最新日期並列時，清空該組舊日期與取消狀態，保留本次可驗證的日期並回報摘要。
6. 寫入前用同一個未鎖定的 SQLite connection 檢查 `data_version` 與快照資料；快照若在明細查詢期間被其他程序替換，取消所有補寫。

## 取捨

- 以單一 SQLite 連線短交易寫入補查結果；網路請求期間不持有資料庫鎖。
- 同日期並列時不靠工作單號猜測先後，避免錯誤標記。
- 快照仍按既有模式完整替換；重跑會重新計算全部候選。
- 本階段只新增本機標記，不因重複判定刪除當次 SQLite 列，也不對 MMIS 發送寫入事件。下一次快照刷新仍取代上一輪快照。

## 設計候選整合

採用兩個候選共同建議的既有 wrapper 內 reconciliation 與短交易更新。拒絕匯入明細 CLI handler，遵守架構地圖的 CLI/domain 邊界；改用 domain reader。日期相同時採 fail-closed，而不以工作單號作業務排序。
