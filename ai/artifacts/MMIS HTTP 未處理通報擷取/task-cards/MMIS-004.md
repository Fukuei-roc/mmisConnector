# AI-Ready 任務卡

## Metadata

- 任務：實作未處理通報查詢與 JSON CLI
- 上層規格：`feature-spec.md`
- 上層 Epic：MMIS HTTP 未處理通報擷取
- 上層 User Story：查詢並輸出故障通報 JSON
- 分軌：後端
- 前置任務（dependsOn）：MMIS-003
- 狀態：就緒（2026-09-21 人工核准）
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標

重播 Maximo event sequence，解析全部結果列並輸出標準 JSON。

## 情境包（Context Pack）

- 相關檔案：錄製 timeline/HAR/DOM、`query_unprocessed_fault_notices.py`、`parser.py`、`cli.py`
- 既有模式：refresh start center、changeapp、query menu click、saved query click
- 假設：表格 column index 1..17 的語意維持穩定
- 未知事項：查無資料回應的局部 DOM 形式
- 允許變更的檔案：Python 套件、測試、README、驗證報告
- 不得觸碰：錄製來源、其他 skills

## 驗收標準

- 完整流程無瀏覽器依賴。
- stdout 是 UTF-8 JSON，`count == len(records)`。
- 解析錄製 DOM 得到 16 筆與 17 個欄位。

## 驗證契約

- 單元測試：錄製 DOM、空欄、checkbox、錯誤回應。
- 整合測試：event payload 順序與 state reuse。
- E2E 測試：live MMIS 一次。
- 安全性檢查：不輸出 session/token/password。
