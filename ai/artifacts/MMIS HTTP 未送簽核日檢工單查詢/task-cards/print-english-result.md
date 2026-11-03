# AI-Ready 任務卡

## Metadata

- 任務：以英文顯示未送簽核日檢工單查詢執行結果
- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP 未送簽核日檢工單查詢
- 上層 User Story：內部使用者執行指令後，直接確認是否成功、筆數與資料庫位置
- 分軌：後端 CLI
- 前置任務：`snapshot-sqlite.md` 已完成
- 狀態：完成
- 風險等級：中；變更 CLI 輸出，不改查詢或資料庫寫入
- Agent owner：Codex
- 人工核准者：使用者於 2026-11-03 明確要求實作與驗證

## 目標

指令以英文文字顯示執行狀態、查詢筆數與資料庫相對路徑，不列印逐筆資料。

## 情境包（Context Pack）

- 相關檔案：development tool、`_support.py`、對應測試與工具 README。
- 既有模式：`execute()` 完成查詢與 SQLite 寫入並回傳摘要；`main()` 處理 CLI 輸出。
- 假設：英文文字輸出較適合人工直接查看；失敗時筆數不可得，顯示 `unavailable`。
- 未知事項：Live MMIS 當次資料筆數可能變動。
- 允許變更的檔案：本工具、對應測試、工具 README、本 Epic 規格、任務卡與驗證報告；清理不再使用的共用輸出旗標。
- 不得觸碰：MMIS 查詢條件、資料表結構、其他工具的輸出行為、憑證檔。
- 情境預算：閱讀本工具、共用 CLI 包裝器、對應測試及既有規格；跳過無關的查詢模組。

## 需求與驗收標準

- 成功輸出 `Status: SUCCESS`、本次筆數及資料庫相對路徑，結束碼為 0。
- 失敗輸出 `Status: FAILED`、不可用筆數、資料庫相對路徑及英文例外類別，結束碼為 1。
- 不輸出逐筆工單、憑證或原始例外訊息；其他 development tool 的 JSON 輸出不變。

## 驗證契約

- 單元測試：成功與失敗輸出、結束碼、資料庫內容。
- 整合測試：全套 pytest。
- E2E 測試：執行實際指令，核對輸出筆數與 SQLite 筆數。
- 型別檢查與 Lint：專案未設獨立指令。
- Build：`python -m compileall -q`。
- 螢幕截圖：無 UI。
- 安全性檢查：錯誤不列印敏感訊息，資料庫路徑為固定專案路徑。

## 完成證據

- 見 `../verification/print-english-result.md`。
