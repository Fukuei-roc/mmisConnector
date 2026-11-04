# AI-Ready 任務卡

## Metadata

- 任務：補查重複日檢工單開單日期並標示取消候選
- 上層規格：`../feature-spec.md`
- 上層 Epic：自動刪除重複開立的日檢工單
- 上層 User Story：建立可人工檢查的重複工單取消候選清單
- 分軌：後端
- 前置任務（dependsOn）：`collect-unassigned.md`
- 狀態：審查中；程式與驗證完成，里程碑優先規則待使用者確認
- 風險等級：高，MMIS HTTP 查詢與本機 SQLite 快照
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-04 明確要求

## 目標

刷新快照後，查詢重複車組的每張工單開單日期，並將不是唯一最新工單的其他列標記為「待工單取消」。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_delete_duplicate_daily_inspection_work_orders.py`、`src/mmis_connector/daily_inspection/reader.py`、`src/mmis_connector/daily_inspection/unassigned.py`、`tests/test_unassigned_daily_inspection_work_orders.py`、`tools/mmis_development/README.md`。
- 既有模式：先完整查詢並交易式替換 SQLite 快照；以 `DailyInspectionWorkOrderDetailReader.open_detail()` 和 `parse_daily_inspection_basic_info()` 讀取基本資料；重用單一 MMIS session。
- 假設：開單日期格式為 `YYYY/MM/DD HH:mm`；同一最新日期並列時無法判定唯一保留項，該組不標記取消。
- 未知事項：重新查詢後是否符合 EMU929／115-1A-81454 里程碑。
- 允許變更的檔案：本任務卡所列程式、測試、development tools README、本 Epic 規格、架構計畫及驗證紀錄；使用者忽略的 SQLite 快照依要求更新。
- 不得觸碰：MMIS 遠端寫入、取消或刪除工單、依重複判定刪除當次 SQLite 快照列、production application 模組。快照刷新仍依前置任務的既有行為取代前次快照。

## 需求

- 在「查詢時間」後、「執行結果」前新增「開單日期」。
- 重複車組的每張工單均須成功讀取且驗證工作單與車組一致後，才可判斷該組。
- 唯一最新工單保留空白執行結果；其餘列標記「待工單取消」。
- 查詢失敗、日期無效或最新日期並列時不得標記該組。
- 不刪除任何 MMIS 工單或 SQLite 資料列。

## 驗收標準

- 六欄 schema 順序正確，開單日期預設空白。
- 合成資料驗證最新日期保留、較舊資料標記取消。
- 不完整或日期並列群組沒有取消標記。
- 刷新 MMIS 快照後驗證 EMU929／115-1A-81454。
- 使用者指定 115-1A-81454 應為取消候選；實際 MMIS 日期排序目前與此期待衝突，等待確認優先規則。

## 驗證契約

- 單元測試：測試 schema、最新工單、失敗與日期並列。
- 整合測試：以真實唯讀 MMIS 快照執行 development tool，直接查 SQLite 證明欄位與標記。
- 安全性檢查：確認沒有 MMIS 寫入 event、資料列刪除或未參數化 SQL。
- 型別檢查／Lint／Build：執行適用的 compileall 與 pytest。

## 完成證據

- 變更的檔案：development tool、development tools README、功能規格、架構計畫、任務卡、驗證報告與單元測試。
- 執行過的指令：目標 pytest、compileall、git diff check、development tool live 查詢、SQLite 直接讀回。
- 測試輸出：7 項目標測試通過；完整測試有 2 項既有架構盤點失敗，細節見驗證報告。
- 已知限制：資料查詢失敗或開單日期並列時，該組不會產生取消標記。
- 後續任務：人工檢視「待工單取消」資料；實際取消工單需另行核准與設計。
