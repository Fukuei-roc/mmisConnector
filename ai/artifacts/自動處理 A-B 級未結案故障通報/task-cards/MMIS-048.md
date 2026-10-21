# AI-Ready 任務卡

- 任務：MMIS-048 條件式檢查故障分析資料充分性
- 上層 Epic：自動處理 A-B 級未結案故障通報
- User Story：條件式檢查故障分析資料充分性
- 狀態：完成；人工核准：使用者 2026-10-20 明確指示
- 風險：高（付費 AI API、MMIS 唯讀網路查詢、本機 SQLite 更新）
- 前置任務：MMIS-047（完成）

## 情境包

- 相關檔案：`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`、`tools/mmis_development/query_fault_notice_full_detail.py`、`src/mmis_connector/fault_notices/analysis_readiness.py`、相關測試及 Development Tool README。
- 既有模式：逐筆普通明細查詢、六欄型別驗證、單筆 SQLite transaction、完整明細的 `--check-analysis-readiness`。
- 範圍：正常執行時只對故障分析未完成的通報再次查資料充分性；保留明確旗標與等候結案規則。
- 非目標：MMIS mutation、AI 故障分析文章、Production CLI、修改認證或 HTTP event。
- 未知：Live MMIS 與 OpenAI 實際回應；僅做離線測試。
- 驗證：mock 明細與 AI 結果、暫存 SQLite、完整 pytest、compileall、pip check、diff check。
- 情境預算：讀取指定工作流程、主工具、完整明細、AI readiness、相關測試與 README；略過無關 UI 與工單寫入流程。

## 驗收標準

- 首輪 `Fault Analysis Completed = false` 才呼叫第二次明細查詢，並只更新 `Sufficient Data for Fault Analysis` 為 SQLite `1` 或 `0`。
- 首輪 `true` 不呼叫 AI，第一欄維持 `NULL`；第二次結果通報號或型別錯誤不得寫入。
- 第二次查詢或寫入失敗時保留首輪五項檢查值，JSON 回報失敗及部分進度。
- 若失敗明確屬於相關工單證據不完整，保留該筆資料充分性 `NULL`、繼續後續通報，回報 `partial_success`、未完成清單與非零 exit code；不得假設為 false 或重試整筆確定性錯誤。
- 既有明確旗標、等候結案名單、主資料庫 schema 與 MMIS 唯讀行為不變。
