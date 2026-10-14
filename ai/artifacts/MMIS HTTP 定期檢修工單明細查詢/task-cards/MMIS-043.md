# MMIS-043 定期檢修工單基本資料

## Metadata

- 上層規格：`../feature-spec.md` 2026-10-14 基本資料擴充
- 上層 Epic：MMIS HTTP 定期檢修工單明細查詢
- 上層 User Story：查詢定期檢修工單的基本資料
- 分軌：後端；前置任務：無
- 狀態：待人工驗收；風險：中（沿用唯讀 MMIS HTTPS session）
- 人工核准：使用者於 2026-10-14 指定指令、錄製檔、六欄與 JSON 位置。

## 情境包

- 相關檔案：`src/mmis_connector/periodic_inspection/reader.py`、`tests/test_periodic_inspection_work_order_details.py`、`tools/mmis_development/README.md`、指定錄製 DOM。
- 既有模式：HTTP reader 已取得唯一工單的明細回應；同類工單以 `label[for]` 關聯欄位，日期空 `value` 時依序讀 `title`、`dojovalue`。
- 假設：六欄均在已取得的工單明細回應中；六欄直接位於 JSON 第一層。
- 未知事項：其他工單的空日期與可見重複欄位尚未即時驗證。
- 允許變更：定期檢修 reader、對應測試、development tool README、本 Epic 產出物、對應看板卡。
- 不得觸碰：登入、event transport、其他 domain、錄製 HAR、憑證。
- 情境預算：讀專案流程與地圖、目標 reader 與測試、同類基本資料解析、指定錄製 DOM；未讀完整 HAR，因本次不改 HTTP event 流程。

## 驗收與驗證契約

- 在 `success` 後、`維修程序概況` 前直接輸出六個第一層欄位，順序及指定工單內容符合規格，不輸出 `基本資料` 物件。
- 使用欄位標籤定位，不固定動態 id；日期可從 `title` 或 `dojovalue` 讀取。
- 缺欄、重複衝突及工作單不符時拒絕輸出成功結果。
- 執行目標 pytest、全套 pytest、編譯、`git diff --check` 與指定工單即時唯讀查詢。
- 無 UI 或資料遷移；權限沿用 MMIS session，無遠端寫入。

## 完成證據

- 驗證與審查：`../verification/MMIS-043.md`。
- 已知限制：其他工單的 DOM 差異尚未即時驗證。
