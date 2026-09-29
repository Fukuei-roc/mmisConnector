# AI-Ready 任務卡

## Metadata

- 任務：整理 MMIS 功能依賴與開發參考架構
- 上層規格：2026-09-29 使用者核准的 repository 架構整理需求
- 上層 Epic：MMIS 開發架構整理
- 上層 User Story：建立可持續的 MMIS 功能開發與依賴規範
- 分軌：不適用
- 前置任務（dependsOn）：`MMIS-001`、`MMIS-002`、`MMIS-013`、`MMIS-014`、`MMIS-015`、`MMIS-016`
- 狀態：完成
- 風險等級：低
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-29 明確要求執行）

## 目標

以實際 import、建構與測試證據釐清 auto-link dependency graph，文件化 production／CLI／reference 邊界，且不改變既有 runtime 行為。

## 情境包（Context Pack）

- 相關檔案：根 README、全部 `src/mmis_connector/`、相關 tests、架構與搜尋 context、看板 artifacts。
- 既有模式：CLI 建構 application/service；Query／Reader／Linker 重用 event transport 與同一 session；parser 解析動態 Maximo DOM；SQLite 保存批次狀態。
- 假設：使用者本次明確指令即為低風險文件／測試整理的人工核准；任何 Live mutation 仍需另行核准。
- 未知事項：repository 外 Recorder evidence 的完整內容不在本次搬移範圍。
- 允許變更的檔案：README、development docs、架構測試、持久性 context 與本任務治理 artifacts。
- 不得觸碰：production runtime module、SQLite runtime data、Recorder 原始 evidence、Live MMIS 資料。

## 需求

- 明確區分核心對 reusable components 的依賴與四個 CLI entry points。
- 評估四個 CLI、所有正式 module 與現有 evidence 的定位。
- 建立長期開發搜尋與 reference 保存規則。
- 以最小測試保護 application 不依賴 CLI／subprocess。
- 更新 README；不為整理而重寫已驗證 Maximo flow。

## 驗收標準

- Dependency graph 包含 direct 與 transitive dependencies。
- 四個 CLI 的保留理由與 runtime 邊界有文件記錄。
- 未移動 reusable production module；若沒有 artifact 可搬，明確記錄為零搬移。
- Auto-link business、SQLite 與 JSON contract 未修改。
- 指定四項離線驗證全數通過，pytest 結果與 119 passed、3 skipped baseline 比較。

## 實作備註

- 詳細架構決策見 `architecture-plan.md`。
- 不建立沒有內容的 reference／experiments 目錄。
- 架構測試解析 Python AST，不 import 或執行 Live workflow。

## 驗證契約

- 單元測試：`tests/test_architecture.py`。
- 整合測試：既有 auto-link、store 與 CLI tests；完整 pytest。
- E2E 測試：不執行 Live MMIS；本次無 runtime 行為變更。
- 型別檢查：專案未配置。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tests`、`python -m pip check`。
- 螢幕截圖：不適用，無 UI。
- 安全性檢查：確認無敏感 evidence、新網路呼叫、subprocess 或 runtime dependency。

## 完成證據

- 變更的檔案：README、development guide、架構測試、持久性 context 與本任務治理 artifacts；production runtime 無變更。
- 執行過的指令：針對性 pytest、完整 pytest、compileall、pip check、diff check、JSON 格式與敏感資料掃描。
- 測試輸出：44 項針對性測試通過；完整回歸 121 passed、3 optional fixture skipped。
- 螢幕截圖：不適用。
- 已知限制：錄製 DOM 位於本機外部路徑，三項 optional 測試可能 skip。
- 後續任務：若新增可執行探索腳本，再依 guide 建立 `development/experiments/`；合理新增 dependency 時同步更新架構 allowlist。
