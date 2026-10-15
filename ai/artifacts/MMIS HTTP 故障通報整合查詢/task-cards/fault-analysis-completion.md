# AI-Ready 任務卡

## Metadata

- 任務：完整故障通報輸出故障分析填寫完成狀態
- 上層規格：本次使用者需求，三欄判定規則已明確
- 上層 Epic：MMIS HTTP 故障通報整合查詢
- 上層 User Story：查詢故障通報的故障分析填寫狀態
- 分軌：後端
- 前置任務：既有完整故障通報查詢
- 狀態：完成
- 風險等級：低（只讀已解析資料，不新增網路事件）
- Agent owner：Codex
- 人工核准者：使用者於本次訊息直接要求新增欄位

## 目標

在完整故障通報 JSON 的「故障分析素材」前，加入 `Fault Analysis Completed` 布林欄位。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/query_fault_notice_full_detail.py`、`src/mmis_connector/fault_notices/full_detail.py`、`tests/test_fault_notice_full_detail.py`。
- 既有模式：Reader 已用 label/for 解析「故障分析」頁籤五欄；wrapper 依序組裝 JSON。
- 假設：需求中「有一不是空白則 false」依後句「全部都有文字則 true」解讀為「有任一欄空白則 false」。
- 未知事項：無。
- 允許變更的檔案：完整通報 wrapper、相關測試與此 Epic 的任務及驗證紀錄。
- 不得觸碰：MMIS 身分驗證、事件流程、其他查詢和寫入功能。
- 情境預算備註：僅讀專案地圖、相關 Reader/wrapper、目標測試及指定錄製摘要與 DOM；未讀敏感 HAR。

## 需求與驗收標準

- 三欄「故障原因」、「處理情形」、「改善對策」都含至少一個非空白字元時為 `true`；任一欄為空字串或純空白時為 `false`。
- 單一字元有效；欄位資料取自既有 MMIS 故障分析解析結果。
- 狀態欄緊貼「故障分析素材」前；`--ai-analysis` 不改變已從 MMIS 讀取的狀態。

## 驗證契約

- 單元測試：單字元、空字串、純空白與三欄組合。
- 整合測試：錄製 DOM 解析；執行目標通報 CLI 並檢查布林值與順序。
- 安全性檢查：不新增網路請求、不儲存錄製敏感資料。
- 螢幕截圖、型別檢查、Build：CLI 輸出欄位變更，不適用。

## 完成證據

- 見 `../verification/fault-analysis-completion.md`。
