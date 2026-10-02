# AI-Ready 任務卡

## Metadata

- 任務：在整合查詢 JSON 置頂加入故障通報基本資料
- 上層規格：`ai/artifacts/MMIS HTTP 故障通報整合查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 故障通報整合查詢
- 上層 User Story：整合查詢
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002、MMIS-027（已實作）
- 狀態：完成（使用者確認測試正常）
- 風險等級：高（既有認證及內網唯讀查詢）
- Agent owner：Codex
- 人工核准者：使用者於 2026-10-02 明確要求修改本命令 JSON

## 目標

在既有整合查詢輸出的第一層最前面加入六個基本欄位，通報號只輸出一次，其餘項目維持原順序與內容。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/fault_notices/full_detail.py`、`src/mmis_connector/parser.py`、`tests/test_fault_notice_full_detail.py`、本機 `2026-10-02_query-fault-notice-basic-information` 錄製 DOM。
- 既有模式：單次精確通報明細、label/for 語意解析、日期 input 的 `value` 或 `dojovalue`。
- 已確認：使用者要求六欄直接位於第一層，不使用 `查詢故障通報基本資料` 包裝項；同名標籤重複時要求值一致。
- 未知事項：無阻擋事項。
- 允許變更的檔案：上述 parser、整合 reader、相關測試、本 Epic 規格／驗證產出物與必要知識更新。
- 不得觸碰：使用者既有的 `Prompt.md`、四個獨立查詢命令公開契約、認證與遠端寫入流程。

## 需求

- 第一層基本資料順序：通報號、事故等級、狀態、發生日期、車次、車組/車號；通報號不得重複。
- 事故現象只保留在既有故障分析，不在基本資料重複。
- 從已開啟的通報明細讀取，不新增登入、查詢或頁籤請求。

## 驗收標準

- 前六個頂層鍵為指定基本欄位，沒有包裝項或重複通報號；後續 ATP 標記、工單與分析鍵維持既有順序。
- 日期在 input value 空白時取畫面顯示日期；重複標籤值矛盾或通報號不符時，輸出 JSON 錯誤，不輸出部分資料。
- 錄製 DOM 與唯讀 live 查詢可讀取六欄；完整測試無回歸。

## 驗證契約

- 單元／整合：欄位解析、日期回退、同名一致與不一致、JSON 順序、既有功能測試。
- E2E：對指定通報號做一次唯讀 live 查詢。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tools`。
- UI 截圖：無 UI 變更，不適用。
- 安全性檢查：不輸出憑證或錄製敏感資料；不新增網路及寫入事件。

## 完成證據

- 變更及測試證據：見 `verification/MMIS-028.md`。
