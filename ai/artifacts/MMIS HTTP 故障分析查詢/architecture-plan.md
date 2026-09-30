# 架構筆記

- 在 `fault_notices/reader.py` 建立 `FaultNoticeAnalysisReader`，不建立第二套 transport。
- 沿用 `MaximoEventClient.load_app/post_events/post`；築選使用同一 POST 的 `setvalue + filterrows`。
- 由 `parse_maximo_table_schema` 解析「通報號」欄位，再核對唯一結果、分頁 total 與完全相符業務鍵。
- 新增通用的 semantic parser：以 title 找唯一 tab，以 label/for 找唯一 textarea；不寫死動態 ID。
- tool 僅驗證一個參數、登入、呼叫 Reader 與輸出 JSON。
- 高風險來源為認證與內網存取；無 mutation、無檔案、無資料庫。回滾只需移除新增程式與 export。
- 審查關卡：產品與高風險人工核准來自 2026-09-30 使用者明確開發請求；仍需完成架構、安全、測試與 code review。
