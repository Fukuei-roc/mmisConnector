# AI-Ready 任務卡：MMIS-044

## Metadata

- 任務：擴充完整通報查詢，整合故障分析素材
- 上層規格：`ai/artifacts/MMIS HTTP 故障分析查詢/feature-spec-analysis-materials.md`
- 上層 Epic：MMIS HTTP 故障分析查詢
- 上層 User Story：由完整通報取得關聯工單明細
- 分軌：後端
- 前置任務：現有完整通報、臨修、日檢、定檢 Reader 均已實作
- 狀態：完成（2026-10-14）
- 風險等級：高（既有認證與唯讀網路）
- Agent owner：Codex
- 人工核准者：專案使用者，於 2026-10-14 明確要求直接實作

## 目標與情境包

- 目標：保持原通報 JSON，最後加入三類故障分析素材。
- 相關檔案：`fault_notices/full_detail.py`、三類工單 `reader.py`、`auth.py`、`tools/mmis_development/query_fault_notice_full_detail.py`。
- 既有模式：development tool 薄封裝；正式 domain component 使用同一 `MMISSession`；HTTP 與 Maximo event 由既有元件處理。
- 假設：段修工單每列以 `工作單` 提供工作單號；Reader 成功回傳 `success: true`。
- 未知事項：實際 MMIS 網路可用性與資料是否仍存在，需 live 查詢確認。
- 允許變更：新增素材模組、完整通報 wrapper、測試、相關 CLI／架構／治理文件。
- 不得觸碰：MMIS 認證、三類 Reader 的既有回傳內容、無關功能。
- 情境預算：只讀四個工具、其 Reader／底層錯誤封裝、相關測試及專案地圖；略過無關 UI 與資料庫模組。

## 驗收與驗證契約

- 六種工作單代碼分類、指定欄位與完整 records、空陣列、多筆同類、重複號碼、單筆失敗。
- 網路第一／第二次恢復、三次失敗、非網路不重試、一秒等待。
- 原 JSON 頂層與順序不變；stdout JSON；CLI 相容。
- `python -m pytest tests/test_fault_notice_analysis_materials.py tests/test_fault_notice_full_detail.py -q`。
- `python -m pytest -q`、`git diff --check`；可用時執行指定通報號 live 唯讀查詢。
- UI 螢幕截圖不適用；安全審查檢查認證共用、同源網路與錯誤訊息。

## 完成證據

- 變更：新增素材整合模組與 mock 測試；完整通報 wrapper 最後附加素材；同步 CLI、架構清單與治理文件。
- 測試：227 passed，32 項因缺少本機錄製 DOM/HAR 而 skipped；compileall、pip check、diff check 通過。
- Live：`1150910-14` 的兩筆臨修與一筆日檢明細均成功取得；定檢陣列為空。
- 已知限制：此通報不含定檢工單，2A/3A 已以 mock 測試；其他 MMIS DOM 差異仍需個案驗證。
