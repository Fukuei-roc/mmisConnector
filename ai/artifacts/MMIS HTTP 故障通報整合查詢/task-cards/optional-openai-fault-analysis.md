# AI-Ready 任務卡

## Metadata

- 任務：為完整故障通報工具加入可選 AI 分析
- 上層規格：`../feature-spec-ai-analysis.md`
- 上層 Epic：MMIS HTTP 故障通報整合查詢
- 上層 User Story：查詢後產生三欄故障檢討
- 分軌：後端
- 前置任務：無
- 狀態：審查中
- 風險等級：高
- Agent owner：Codex
- 人工核准者：使用者已在本次任務訊息明確授權實作及 Mock 驗證

## 情境包

- 相關檔案：`tools/mmis_development/query_fault_notice_full_detail.py`、`src/mmis_connector/fault_notices/{full_detail,analysis_materials}.py`、`auth.py`、`SystemPrompt.md`、`tests/test_fault_notice_full_detail.py`。
- 既有模式：開發工具薄 wrapper；正式元件置於 domain package；`run_json_tool` 維持單一 stdout JSON。
- 假設：目前 `.env` 已有 MMIS 憑證；OpenAI 模型存取權須由帳號確認。
- 未知事項：真實帳號的模型權限與 MMIS 內網可用性。
- 允許變更：AI 元件、完整通報 wrapper、Prompt、依賴與設定範例、相應測試及文件。
- 不得觸碰：MMIS query、Reader、auto-link 寫入邏輯與真實 `.env` 內容。
- 情境預算：讀取架構圖、目標 wrapper、素材組裝、共用 stdout 契約、目標測試及官方 OpenAI 文件；未展開無關頁面解析器。

## 驗收標準

- 無旗標零付費呼叫；旗標路徑完成後合併唯一且最後的「故障分析」。
- API 輸入保留所有工單及原車號，排除既有三欄結論。
- 嚴格輸出結構與條列驗證；暫時性錯誤有限重試，永久錯誤明確失敗。

## 安全與回滾

- Key 僅來自未追蹤 `.env` 或系統環境；錯誤訊息使用固定文字。
- 不修改 MMIS 資料；回滾為移除可選旗標及 AI 元件，原查詢路徑仍可使用。
