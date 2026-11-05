# 清查逾期工單架構

`src/mmis_connector/overdue_work_orders.py` 負責 HTTP app 切換、表格解析與分頁檢查。`tools/mmis_development/audit_overdue_work_orders.py` 負責執行入口和 SQLite 快照，保持開發工具依賴正式 component 的既有方向。資料形狀是八個來源字串欄位，加一個空白「備註」欄。

HAR 的 `changeapp` 事件使用 `ZZ_WO_OVERDUE`、焦點 `FavoriteApp_ZZ_WO_OVERDUE`，頁面 app id 是 `zz_wo_overdue`。分頁沿用 `parse_maximo_page_info` 與 Maximo `click` event。資料庫先完成遠端讀取，再於 `BEGIN IMMEDIATE` 交易中重建資料表。SQLite 回滾提供寫入失敗的保護；查詢失敗時不啟動資料庫交易。

安全範圍是本機唯讀 MMIS 查詢和本機資料庫寫入。若表格欄位或分頁結構變動，查詢會報錯，避免以不完整資料覆蓋舊快照。
