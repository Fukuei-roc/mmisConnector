# 架構筆記

- 核准來源：使用者於 2026-10-02 確認六個頂層 JSON 項目並要求開始實作。
- 入口：`tools.mmis_development.query_fault_notice_full_detail` 驗證參數、登入一次、呼叫 domain reader，沿用共用 JSON 錯誤處理。
- Domain：`FaultNoticeFullDetailReader` 重用 `_load_exact_detail`，在同一明細解析 ATP 標記，開啟故障追蹤並讀兩張表，再開故障分析及條件式 ATP 子頁籤。
- 基本資料擴充：在已取得的同一明細回應中，以 label/for 讀取六欄；同名標籤的值必須一致。日期 input value 空白時取顯示用 title，必要時按台北時區解析 dojovalue。不新增 HTTP event。
- 工單分頁：`LinkedWorkOrdersReader.read_records`、`RepairWorkOrdersReader.read_records` 接受已開啟頁籤的回應及下一個 xhr 序號；各自沿用既有欄位、去重、CA 篩選及分頁驗證。四個獨立工具的輸出契約不變。
- 資料契約：第一層依序為通報號、事故等級、狀態、發生日期、車次、車組/車號、是ATP故障、段修工單、CA查修工單、故障分析、ATP故障分析。沒有基本資料包裝項或重複通報號；未勾選時最後一項為 `null`。
- 安全與隱私：重用 `MMISSession`、同源 HTTPS、CSRF 與現有 Maximo event；不增加寫入事件、不落盤業務資料或憑證。
- 遷移與回滾：無資料模型或遷移；回滾僅需移除新入口與 reader，恢復工單 reader 的原迴圈位置。
- 審查關卡：架構、輸入與認證邊界、測試。此唯讀功能不改變授權模型。
