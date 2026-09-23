# AI-Ready 任務卡

## Metadata

- 任務：建立環境變數與密鑰規範
- 上層 Epic：專案設置
- 上層 User Story：環境變數與金鑰設定
- 分軌：後端
- 前置任務（dependsOn）：無
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標

讓真實 credentials 只存在未追蹤 `.env`，並提供安全範例設定。

## 驗收標準

- `.env` 被 Git 忽略。
- `.env.example` 不含真實帳密。
- stdout 不輸出 password、cookie、CSRF token 或 session id。

## 驗證契約

- `git check-ignore -v .env`。
- repo secret pattern 掃描。
- CLI 成功與錯誤 JSON 欄位檢查。
