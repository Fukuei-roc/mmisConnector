# 架構規劃

## 使用方式與資料契約

`python -m tools.mmis_development.query_latest_periodic_inspection_work_order 813` 列印一個含四個中文欄位的 JSON 物件。資料結構是一筆工單，不是清單；無結果視為查詢錯誤。

## 選定結構

- `periodic_inspection/query.py` 持有 `LatestPeriodicInspectionWorkOrderQuery.run(vehicle)`。它驗證輸入，使用現有 `MaximoEventClient` 進入 `ZZ_PMWO`、切所有記錄、依動態表頭找到過濾欄位，並讀完分頁。
- `parser.py` 的表格與分頁解析器負責 Maximo HTML/XML；查詢類別只負責本功能的固定篩選條件、資料完整性及最新日期選取。
- `tools/mmis_development/query_latest_periodic_inspection_work_order.py` 只處理一個位置參數、建構 session 和呼叫 `run_json_tool`。

此次級別條件比較了兩種放法：在既有過濾條件序列插入第四個 `setvalue`，或另加一段級別專用事件邏輯。選擇前者，因為動態表頭與事件順序已由同一段程式管理；後者會重複欄位定位及 XHR 序號規則。

比較過直接重用 `DailyInspectionWorkOrderQuery`：該類別綁定日檢 app、日期參數與單頁結果，重用會混入不同業務規則。新建同領域的小型 query 更符合現有模組分層。與既有定期檢修明細 reader 共享 HTTP/event/parser，不將清單查詢塞入明細 reader。

## 邊界、測試及回滾

- 輸入：去除前後空白，禁止空值。MMIS 依車號、檢修級別 `2A,3A`、檢修單位、工單狀態的順序設定過濾器，再按車號邊界檢查結果。
- 外部資料：選入列只能是 `2A` 或 `3A`；要求四欄存在、所有頁面筆數與範圍一致、日期合法。相同檢修日期以工作單號字典序選一筆。
- 身分驗證及網路：沿用 `MMISSession` 的環境變數、HTTPS 與程序內 session；不新增憑證儲存或網路端點。所有查詢唯讀。
- 驗證：合成跨頁與錯誤測試、指定錄製資料核對、完整 pytest、CLI 實際輸出、編譯與 diff 檢查。沒有 UI 變更。
- 遷移：無。回滾為移除新增查詢模組、wrapper、對應測試與文件列項。
