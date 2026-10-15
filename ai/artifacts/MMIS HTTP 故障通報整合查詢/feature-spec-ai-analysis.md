# 功能規格書：可選的 OpenAI 故障分析

## Metadata

- 功能：完整故障通報查詢後的三欄 AI 故障檢討
- 負責人：Codex
- 狀態：已實作；由使用者提供的具體需求授權
- 風險等級：高（外部 API、密鑰、內部維修資料）

## 問題與目標

完整通報查詢已有事故、工單與分析素材，但三欄檢討需要依 `SystemPrompt.md` 重新產生。使用者以明確旗標啟用付費 API，原查詢保持不變。

## 非目標

- 不修改 MMIS 查詢或正式自動勾稽流程。
- 不根據車號篩選工單。
- 不進行未授權的真實付費 API 呼叫。

## 資料與 API 契約

- 輸入：完整通報 JSON 的深拷貝；排除舊的故障原因、處理情形、改善對策，保留其餘欄位。
- Prompt：根目錄 `SystemPrompt.md` 為規則，`UserPrompt.md` 為當次資料模板。
- API：OpenAI Python SDK Responses API，strict JSON Schema，恰好三個字串欄位。
- 輸出：沿用唯一的頂層「故障分析」物件，更新三欄並將該物件置於最後。
- 錯誤：單一 JSON 錯誤物件與非零狀態；不輸出部分分析及憑證。

## 驗收與驗證

- 原 CLI 無旗標時不呼叫 OpenAI，JSON 不變。
- 帶旗標時保留原始欄位、跨車號與多筆工單資料，且無舊結論污染。
- 驗證格式、重試界限、缺少 Key 與 API 失敗；以 Mock API 測試，不做付費呼叫。
- 執行 `python -m pytest`、`python -m compileall -q src tests tools/mmis_development`、`git diff --check`。
