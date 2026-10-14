# MMIS-041 定期檢修工單重要事項紀錄

## Metadata

- 上層規格：`../feature-spec.md` 2026-10-14 擴充
- 上層 Epic：MMIS HTTP 定期檢修工單明細查詢
- 上層 User Story：查詢工單紀事(備註)清單
- 分軌：後端；前置任務：MMIS-040（已完成）
- 狀態：完成；風險：中（已驗證的唯讀 MMIS HTTPS 流程）
- 人工核准：使用者於 2026-10-14 明確要求此實作及輸出欄位。

## 情境包

- 相關檔案：`src/mmis_connector/periodic_inspection/reader.py`、`src/mmis_connector/temporary_repair/reader.py`、`src/mmis_connector/parser.py`、`tests/test_periodic_inspection_work_order_details.py`。
- 既有模式：共用 `MaximoEventClient`；以表格 summary 與欄名定位；核對分頁範圍、總筆數與下一頁。
- 假設：錄製資料中表格位於「檢修回報」回應；九欄均為清單欄。
- 未知事項：其他工單是否有多頁紀事，故以合成測試驗證。
- 允許變更：定期檢修 reader、對應測試、development tool README、本 Epic 產出物。
- 不得觸碰：登入、event transport、其他 domain、錄製 HAR、憑證。
- 情境預算：讀取專案地圖、架構與搜尋指南、兩支 reader、共用 parser、對應測試及錄製 DOM；未掃描其他 domain 全檔。

## 驗收與驗證契約

- `維修程序概況` 在 `檢修記錄` 前；count 與 records 對應所有紀事列，每列九欄。
- 零筆與多頁可處理；缺表、缺欄或分頁不連續時拒絕輸出不完整資料。
- 執行 `python -m pytest tests/test_periodic_inspection_work_order_details.py -q`、`python -m pytest -q`、`git diff --check`，並以指定工單即時唯讀查詢。
- 無 UI、資料模型遷移或遠端寫入；權限沿用 MMIS session。

## 完成證據

- 驗證與審查：`../verification/MMIS-041.md`。
- 已知限制：實際錄製清單只有一頁，跨頁以合成測試覆蓋。
