# AI-Ready 任務卡

## Metadata

- 任務：新增 ATP 故障分析 AI 分類建議
- 上層規格：`../feature-spec-atp-ai-classification.md`
- 上層 Epic：MMIS HTTP 故障通報整合查詢
- 上層 User Story：在完整通報 AI 分析時獨立建議 ATP 三層分類
- 分軌：後端
- 前置任務：既有完整通報、故障分析素材及選項遍歷功能已完成
- 狀態：完成（待人工驗收）
- 風險等級：高
- Agent owner：Codex
- 人工核准者：使用者於 2026-10-16 任務訊息明確授權直接開發、整合及測試

## 目標與情境包

- 目標：`--ai-analysis` 且布林 ATP true 時一律產生獨立、合法的 ATP 建議。
- 相關檔案：`query_fault_notice_full_detail.py`、`ai_analysis.py`、`atp_options.py`、`export_atp_fault_analysis_options.py`、`atp_fault_analysis_options.json`、`tests/test_fault_notice_ai_analysis.py`。
- 既有模式：單一 MMIS Session；完整通報與工單素材只查詢一次；OpenAI 設定與有限重試由既有 AI 元件提供；Prompt 在 `prompts/`。
- 假設：現有完整選項遍歷 JSON 可供載入；Live MMIS 與 OpenAI 帳號可用。
- 未知事項：後續重新遍歷時選項樹是否變更。
- 允許變更：ATP 選項 JSON 路徑、選項遍歷輸出、ATP Prompt/元件、完整通報 tool、相關測試與本 Epic 產出物。
- 不得觸碰：兩份指定 README、MMIS 查詢／寫入元件與密鑰。
- 情境預算：讀取專案地圖、流程、重構參考、AI 元件、完整通報 tool、選項樹及相關測試；未展開不相關 MMIS DOM 解析器。

## 驗證契約

- 單元／整合：ATP 觸發矩陣、Prompt 隔離、選項樹路徑驗證、空分支／同名分支、失敗保留資料、既有 AI 回歸。
- 全套測試：`python -m pytest -q`。
- 靜態：`python -m compileall -q src tools/mmis_development tests`、`python -m pip check`、`git diff --check`。
- Live：`python -m tools.mmis_development.query_fault_notice_full_detail 1151012-36 --ai-analysis`。
- 安全性：確認 OpenAI 不接收 MMIS 原 ATP 分類；無 MMIS 業務寫入；錯誤不含密鑰。
- 回滾：移除新 ATP AI 元件及 hook，選項 JSON 與遍歷輸出路徑需成對回復。
