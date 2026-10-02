# 驗證報告：MMIS-026

## 變更與行為

- 新增 `FaultNoticeATPAnalysisReader` 與單參數 development tool。
- 重用既有通報號精確查詢；先檢查 ATP 勾選，再依序點擊兩個頁簽，以 label/for 只讀取三個指定 input 欄位。
- 未勾選時輸出指定訊息的 JSON 錯誤並停止；空欄輸出空字串；無瀏覽器與結果檔。

## 證據

- `python -m pytest --tb=no -ra`：164 passed、9 skipped；skips 為其他本機錄製檔缺席，ATP 本次錄製 DOM 測試已執行。
- `python -m compileall -q src tests tools/mmis_development`：通過。
- `python -m pip check`：`No broken requirements found.`
- `git diff --check`：通過；僅顯示 Git 對工作樹換行格式的提醒。
- `python -m tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice invalid`：JSON 參數錯誤、exit 1；在登入前拒絕。
- `python -m tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice 1150210-36`：exit 0；成功 JSON，只含故障要因「設備故障」、故障因子「04.BTM感應子傳輸模組」、故障項目「BTM感應子傳輸模組」，與錄製 DOM 一致。
- 錄製 HAR 核對：詳情回應含 `ATP故障： 已勾選`；主頁簽及 ATP 子頁簽各為一次 click event。
- UI 截圖：不適用，未變更 UI。

## 審查與殘留風險

- 架構：沿用現有 `MMISSession`、`MaximoEventClient` 與通報明細 reader；development wrapper 不承載 domain 邏輯。
- 安全：僅唯讀查詢與導覽 event；未新增憑證、cookie、HAR、token 寫入或瀏覽器依賴。
- 測試：已覆蓋 ATP 勾選／未勾選、勾選狀態不一致、頁簽順序、三欄、排除其他欄位、空值、缺欄與錄製 DOM。未勾選的 live 通報號未提供，該分支以離線測試驗證。
- 殘留風險：MMIS 未來若變更 checkbox alt/src、頁簽 title 或欄位 label，程式會拒絕解析；若需支援新 DOM，應以新錄製證據更新 parser。
- 後續任務：無必要後續任務。
