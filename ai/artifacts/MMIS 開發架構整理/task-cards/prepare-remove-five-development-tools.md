# AI-ready 任務卡：準備移除五個重複查詢入口

## Metadata

- 任務：讓五個單項查詢入口不再被現行程式、測試與指令文件依賴。
- 上層規格：本次使用者要求，屬既有功能的結構整理。
- 上層 Epic：MMIS 開發架構整理。
- 分軌：後端。
- 前置任務：無。
- 狀態：完成。
- 風險等級：低。只改測試與文件，不改 MMIS 或正式執行程式。
- 人工核准者：使用者本次明確核准準備刪除，並要求本次保留五個入口檔案。

## 目標

保留五個入口檔案，但移除 repo 內對它們的依賴，使下次刪除檔案時不影響保留的程式功能。

五個入口為 `query_fault_notice_analysis.py`、`query_atp_fault_analysis_linked_to_fault_notice.py`、
`query_work_orders_linked_to_fault_notice.py`、`query_repair_work_orders_linked_to_fault_notice.py` 與
`query_daily_inspection_work_order_by_number.py`。

## 情境包

- 相關檔案：`tests/test_development_tools.py`、`tests/test_architecture.py`、`tools/mmis_development/README.md`、根目錄 `README.md`、`ai/context/` 與 `docs/development/mmis-feature-workflow.md`。
- 既有模式：正式功能位於 `src/mmis_connector/`；完整通報與日檢明細入口已輸出被移除入口所查的資料。
- 假設：歷史規格、驗證紀錄與已完成看板卡片保留原始證據；外部排程不在本 repo 的依賴掃描範圍。
- 未知事項：外部排程或人工腳本是否仍直接執行五個舊入口。
- 允許變更：現行測試、現行指令文件、架構與專案地圖、本任務產出物。
- 不得觸碰：五個待刪入口、`src/mmis_connector/`、歷史看板卡片、MMIS 資料。

## 驗收標準

- 五個待刪入口仍存在，內容不變。
- 現行 `src/`、`tools/`、`tests/` 與指令文件不依賴其模組名稱。
- 完整通報與日檢明細仍涵蓋原有查詢資料。
- 完整離線測試在禁止 import 五個模組的條件下通過。

## 驗證契約

- 單元與整合測試：`python -B -m pytest -q -o addopts='' -p no:cacheprovider`。
- 模擬刪除：在 `sys.meta_path` 阻擋五個模組的 import，再執行同一測試集。
- 依賴掃描：精確搜尋五個模組名稱，排除五個入口自身與歷史看板卡片。
- 安全性：確認沒有變更登入、網路、MMIS 寫入與密鑰處理。
- UI、型別檢查、建置：不適用。

## 後續任務

取得刪除指示後，移除五個入口並重跑相同驗證。刪除前先確認 repo 以外的排程或腳本。
