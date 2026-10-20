# AI-Ready 任務卡

## Metadata

- 任務：MMIS-047 逐筆查詢並保存等候結案的 A 級通報
- 上層規格：[feature-spec.md](../feature-spec.md)
- 上層 Epic：自動處理 A-B 級未結案故障通報
- 上層 User Story：保存等候結案的 A 級通報
- 分軌：後端
- 前置任務（dependsOn）：MMIS-046（完成）
- 狀態：完成
- 風險等級：高（兩個本機資料庫的寫入）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-20 任務指示）

## 目標

每次完整查詢來源後，略過已等候結案的通報，逐筆查詢其餘通報；符合指定五項檢查值的 A 級通報搬移至不重置的獨立 SQLite。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/auto_process_unclosed_ab_fault_notices.py`、`tools/mmis_development/query_fault_notice_full_detail.py`、`tests/test_auto_process_unclosed_ab_fault_notices.py`、`tools/mmis_development/README.md`。
- 既有模式：完整來源查詢、15 欄全量 snapshot、單筆完整通報 Python 呼叫與六欄回填；資料庫固定於 `data/`。
- 假設：新增日期使用台北時間且保留時區；預設不呼叫 AI，因五項搬移條件均為非 AI 布林值。
- 未知事項：MMIS Live 實際通報筆數及完整查詢時長；本階段不自行連線驗證。
- 允許變更的檔案：既有 development tool、相關測試、Development Tool README、`.gitignore`、本 Epic 規格與治理產出物。
- 不得觸碰：根 README、Production CLI、HTTP event、authentication、parser、retry policy、其他資料庫。
- 情境預算備註：讀取既有工具、相關測試、專案地圖、流程及 MMIS 知識；跳過不相關 UI、工單 mutation 實作。

## 需求

- 英文名稱：A-Level Fault Notices Awaiting Closure；資料庫 `data/a_level_fault_notices_awaiting_closure.db`，資料表同名，兩欄為 `通報號` 與 `新增日期`。
- 已存在等候結案庫的通報不得出現在本次主 snapshot，也不得再次查完整明細；等候結案庫不得重置或覆寫原新增日期。
- 全部待處理通報按本次來源順序查詢。A 級且五欄依序為 true、true、false、false、false 時搬移；B 級不搬移。
- 單筆跨庫搬移使用 transaction；失敗 rollback，先前成功的批次進度保留並在 JSON 指出。

## 驗收標準

- 離線測試涵蓋首跑搬移、次跑跳過、日期保持、五欄各自不符、B 級、錯 schema、搬移 rollback、空來源及中途查詢失敗。
- 不呼叫 MMIS mutation；預設不呼叫 AI；完整查詢工具不使用 subprocess。

## 實作備註

- 將等候結案庫視為持久集合，先載入其通報號，再建主 snapshot。
- `Sufficient Data for Fault Analysis` 不參與搬移條件；明確旗標仍保留 AI opt-in。
- SQLite 以 `ATTACH DATABASE` 在同一 transaction 中插入等候結案庫並刪除主資料表列。

## 驗證契約

- 單元測試：`python -m pytest tests/test_auto_process_unclosed_ab_fault_notices.py`
- 整合測試：`python -m pytest`
- E2E 測試：不自行執行 Live MMIS
- 型別檢查：不適用
- Lint：`git diff --check`
- Build：`python -m compileall -q src tests` 與 `python -m compileall -q tools/mmis_development`
- 螢幕截圖：不適用
- 安全性檢查：SQL 參數化、既有 schema 驗證、跨庫 rollback、逐筆狀態與認證資料不輸出

## 完成證據

- 見 [MMIS-047 驗證報告](../verification/MMIS-047.md)。
