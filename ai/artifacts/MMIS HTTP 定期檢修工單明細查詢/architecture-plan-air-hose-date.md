# 架構規劃：定期檢修工單空氣軟管日期

## 用法與資料模型

```text
python -m tools.mmis_development.query_periodic_inspection_work_order_air_hose_date <工作單>
```

成功結果是一筆工作單與其附表一符合列的 JSON 物件。`records` 每筆只輸出「檢查項目」與「量測值」；來源頁面的其他欄位僅用於解析。資料筆數由 Maximo 頁面決定。

車型映射以一個表表達：`EMU6xx → 600型 / 安裝日期`、`EMU7xx → 700型 / 空氣軟管`、`EMU8xx → 800型 / 空氣軟管`。其他車號正常回傳 `success: true`、`supported: false`、`message: 此工作單非支援的車型`、`count: 0` 與 `records: []`。

## 檔案與責任

- `src/mmis_connector/periodic_inspection/reader.py` 抽出既有工作單明細開啟步驟，供原明細查詢與新附表一查詢共用；新增空氣軟管查詢方法與車型 registry。
- `tools/mmis_development/query_periodic_inspection_work_order_air_hose_date.py` 處理單一 CLI 參數、session 建構及共用 JSON 輸出。
- `tests/test_periodic_inspection_work_order_details.py` 驗證抽出工作單開啟流程的既有查詢回歸；`tests/test_periodic_inspection_air_hose_date.py` 驗證車型分類、過濾事件、欄位資料、無結果與分頁完整性。
- `tests/test_architecture.py` 明列新增的 production domain module 或保持現有 module 清單一致。
- `tools/mmis_development/README.md` 與 `ai/context/project-map.md` 登記新指令。

## 事件流程

1. 依輸入工作單查詢預設定期檢修工單清單。確認為零筆時才切換「所有記錄」重查；結果必須唯一且工作單完全相符。
2. 開啟工單明細，依可見標籤解析工作單與車組/車號。不得依賴 Recorder 中的動態控制項 ID。
3. 不支援車型立即回傳業務結果，不再送出頁籤或附表事件。
4. 依可見文字依序開啟「檢修回報」與「附表一」。若附表過濾器尚未顯示，依動態 toolbar 標籤開啟。
5. 依附表表頭動態找出「檢查項目」欄，送出 `setvalue` 與 `filterrows`；保留原始資料欄位。
6. 依 Maximo 頁面資訊讀完所有結果頁，檢查表格 prefix、總筆數、連續範圍、資料列數、下一頁控制項，並確認每列檢查項目包含所選關鍵字。任何矛盾都以 `MMISClientError` 中止，避免成功回傳不完整清單。

## 安全與風險

- 工作流程只發出讀取與暫態 UI filter/tab event，不送出儲存、送簽或勾稽事件。
- 憑證仍由既有 `.env` 與 `MMISSession` 處理；不讀取、不保存 Recorder 的 cookie、token 或登入識別值。
- 輸入沿用工作單號驗證；所有表格 ID 都由即時回應的 schema 產生。
- 風險等級為高，原因是透過已驗證 session 存取 MMIS 網路。需完成安全性、回歸測試及獨立 diff review。

## 驗證與回復

- 離線測試涵蓋 600/700/800 車型、unsupported、欄位全量、空清單、過濾器開啟、分頁及工作單開啟的既有 fallback 行為。
- 使用指定工作單進行一次即時唯讀查詢，核對回傳車型與附表一資料；若無可用 session，記錄為未執行，不宣稱 live 驗收通過。
- 不涉及持久資料變更；回復方式是還原新增 Reader method、wrapper、文件與對應測試。

## 設計合成

Architect 候選比較後採用候選 A：在現有 periodic inspection Reader 中抽出共用的工作單開啟流程，再新增一個同領域查詢方法。這比額外建立另一個 Reader 與跨物件載體更小，也維持工單定位、狀態和事件序號由同一元件管理。候選 B 的完整分頁範圍與下一頁驗證要求已納入事件流程；輸出記錄必須符合過濾關鍵字也列為 fail-closed 條件。

獨立 cross-judge 對候選 A 評分為 5、5、5、5、4，對候選 B 評分為 3、4、4、4、3。評分依序涵蓋 API 與責任、共用工單開啟、unsupported 行為、動態欄位及分頁、回歸風險。候選 B 的額外 result carrier 未呈現具體需求，因此不採用。
