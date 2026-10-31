# AI-Ready 任務卡：日檢工單檢修段

## Metadata

- 上層規格：`ai/artifacts/MMIS HTTP 日檢檢修記錄查詢/feature-spec.md` 2026-10-31 擴充。
- 上層 Epic：MMIS HTTP 日檢檢修記錄查詢。
- 狀態：完成；使用者於 2026-10-31 指定欄位、位置、工單號及頁面定位資料。
- 風險等級：中。沿用既有唯讀 HTTP session，不新增網路或寫入邊界。
- 人工核准：使用者直接下達實作需求。

## 目標與情境包

- 目標：在日檢工單明細 JSON 的「車次」後加入「檢修段」說明文字。
- 相關檔案：`src/mmis_connector/daily_inspection/reader.py`、`tools/mmis_development/query_daily_inspection_work_order_details.py`、`tests/test_daily_inspection_inspection_records.py`。
- 既有模式：基本資料使用欄位表固定順序，解析結果由 development tool 組裝為第一層 JSON。
- 假設：`aria-label="檢修段 說明"` 輸入框提供顯示文字；指定工單 live DOM 已驗證。
- 未知事項：其他工單的頁面欄位布局是否相同。
- 允許變更：上述三個程式檔及本 Epic 規格、任務卡、驗證報告。
- 不得觸碰：`.env`、錄製檔、MMIS 遠端資料及無關功能。
- 驗證：對應 pytest、完整 pytest、編譯檢查、diff 檢查及指定 live CLI。
- 情境預算：讀取專案與架構地圖、流程、日檢 reader、tool、對應測試及知識庫；未讀無關功能或整份錄製流量。

## 需求與驗收標準

- 成功 JSON 的「車次」後緊接「檢修段」，其值為顯示文字。
- 指定工單 `115-1A-78885` 回傳「新竹機務段」，不回傳代碼 `MHY10`。
- 欄位缺失或多筆值不一致時回傳安全錯誤。
- 原有欄位和資料群組維持原順序及內容。

## 實作與驗證契約

- 在既有基本資料解析中從說明輸入框讀值，並由 tool 插入第一層 JSON。
- 使用測試覆蓋顯示值與代碼差異、欄位順序；執行指定工單 live CLI。
- UI、資料遷移、型別建置及截圖不適用。
