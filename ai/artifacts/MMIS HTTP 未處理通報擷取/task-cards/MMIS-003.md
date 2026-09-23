# AI-Ready 任務卡

## Metadata

- 任務：實作 HTTP 登入與記憶體 Session
- 上層規格：`feature-spec.md`
- 上層 Epic：MMIS HTTP 未處理通報擷取
- 上層 User Story：登入並保持 Session
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002
- 狀態：就緒（2026-09-21 人工核准）
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標

建立不依賴瀏覽器的 MMIS 登入元件，並以同一 `requests.Session` 保持登入狀態。

## 情境包（Context Pack）

- 相關檔案：錄製 HAR/DOM、既有 skill `mmisClient.py`、`src/mmis_connector/auth.py`
- 既有模式：解析 loginform hidden fields、POST `mxlogin.jsp`、跟隨 redirect、解析 page state
- 假設：帳號具有 `ZZ_FNM` 權限
- 未知事項：live MMIS 是否改變登入欄位
- 允許變更的檔案：Python 套件、測試、文件
- 不得觸碰：錄製來源、其他 skills

## 需求

- 從環境變數載入 credentials。
- 不輸出或持久化 credentials/session secrets。
- 驗證登入成功與 page state 完整性。

## 驗收標準

- 登入後持有 cookies 與 start center state。
- 登入失敗輸出安全且可診斷的錯誤。

## 驗證契約

- 單元測試：hidden fields、redirect、page state、失敗訊號。
- 整合測試：fake HTTP sequence。
- 安全性檢查：secret scan 與 stdout 欄位檢查。
