# AI-Ready 任務卡

## Metadata

- 任務：MMIS-045 建立 A/B 級未結案通報 SQLite snapshot
- 上層規格：[feature-spec.md](../feature-spec.md)
- 上層 Epic：自動處理 A-B 級未結案故障通報
- 上層 User Story：建立 A/B 級未結案通報 snapshot
- 分軌：後端
- 前置任務（dependsOn）：無；既有查詢已完成
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：專案使用者（2026-10-19 任務指示）

## 目標

只以完整、成功的既有 A/B 級未結案查詢結果，原子更新固定 SQLite snapshot。

## 情境包（Context Pack）

- 相關檔案：`tools/mmis_development/query_unclosed_fault_notices.py`、`src/mmis_connector/fault_notices/query.py`、`src/mmis_connector/parser.py`、`src/mmis_connector/auto_link/store.py`、`tests/test_query_unclosed_fault_notices.py`、`tools/mmis_development/README.md`。
- 既有模式：Development Tool 直接呼叫正式 Query；Query 已驗證 saved query、固定 A/B 與 depot filters、分頁連續性及總筆數。
- 假設：saved query「故障通報未結案清單」是未結案狀態的權威定義；沒有另一份可重用的狀態列舉。
- 未知事項：本機未提供未結案查詢錄製 DOM；不能獨立驗證 MMIS 當前所有狀態字串。
- 允許變更的檔案：新 tool、新測試、Development Tool README、`.gitignore`、本 Epic 治理產出物。
- 不得觸碰：根 README、Production CLI、authentication、HTTP event、parser、retry policy、現有 Production auto-link。
- 情境預算備註：閱讀查詢／parser／SQLite／相關測試及指定文件；未展開不相關工單、AI、UI 實作。

## 需求

- 依功能規格執行 8 欄擷取、15 欄 schema、7 欄 NULL、通報號唯一及成功全量覆蓋。
- SQL transaction 內驗證 schema、刪除舊列、寫入新列、確認筆數與預留 NULL 後 commit。
- 失敗回傳 JSON 與 exit code 1，不輸出敏感資料。

## 驗收標準

- 功能規格中的所有條件由離線測試涵蓋。
- 無完整明細、AI 或 MMIS mutation 呼叫；未執行 Live MMIS。

## 實作備註

- 直接重用 `UnclosedFaultNoticeQuery.run()`，不以 subprocess 呼叫 CLI。
- SQLite 使用標準函式庫；路徑由 `__file__` 定位專案根目錄。
- 新工具僅屬 Development Tool；不新增 Production CLI。

## 驗證契約

- 單元測試：`python -m pytest tests/test_auto_process_unclosed_ab_fault_notices.py`
- 整合測試：`python -m pytest`
- E2E 測試：不執行 Live MMIS
- 型別檢查：不適用
- Lint：`git diff --check`
- Build：`python -m compileall -q src tests`、`python -m compileall -q tools/mmis_development`
- 螢幕截圖：不適用
- 安全性檢查：schema 驗證、rollback、固定 SQL、無逐筆 stdout 與認證輸出

## 完成證據

- 見 [MMIS-045 驗證報告](../verification/MMIS-045.md)。
