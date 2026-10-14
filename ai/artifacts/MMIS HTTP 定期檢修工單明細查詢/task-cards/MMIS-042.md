# MMIS-042 定期檢修工單維修情形

## Metadata

- 上層規格：`../feature-spec.md` 2026-10-14 維修情形擴充
- 上層 Epic：MMIS HTTP 定期檢修工單明細查詢
- 上層 User Story：查詢定期檢修工單的維修情形
- 分軌：後端；前置任務：MMIS-041（已完成）
- 狀態：待人工驗收；風險：中（沿用唯讀 MMIS HTTPS session）
- 人工核准：使用者於 2026-10-14 指定指令、兩欄及 JSON 順序。

## 情境包

- 相關檔案：`src/mmis_connector/periodic_inspection/reader.py`、`tests/test_periodic_inspection_work_order_details.py`、錄製 DOM 與 HAR。
- 既有模式：原 reader 已取得唯一工單的明細回應；以 `label[for]` 關聯 textarea，解析 Maximo XML/CDATA。
- 假設：兩欄在明細的「動態資料」區塊，與已核對工作單號的回應相同。
- 未知事項：其他工單的欄位內容可能為空，空欄保留為空字串。
- 允許變更：定期檢修 reader、對應測試、development tool README、本 Epic 產出物、對應看板卡。
- 不得觸碰：登入、event transport、其他 domain、錄製 HAR、憑證。
- 情境預算：讀取專案地圖、架構與搜尋指南、既有 reader、對應測試、parser 函式與目標 DOM；未掃描其他 domain 全檔。

## 驗收與驗證契約

- JSON 末尾依序為 `維修情形`、`維修情形(詳述)`，保留換行及空值。
- 同名隱藏欄不混淆；必要欄位缺失或可見欄重複時拒絕輸出部分結果。
- 執行目標 pytest、全套 pytest、編譯與 `git diff --check`，並以指定工單即時唯讀查詢。
- 無 UI 或資料遷移；權限沿用 MMIS session，無遠端寫入。

## 完成證據

- 驗證與審查：`../verification/MMIS-042.md`。
- 已知限制：其他工單的欄位內容及 DOM 差異尚未即時驗證。
