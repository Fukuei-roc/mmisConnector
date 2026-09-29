# AI-Ready 任務卡

## Metadata

- 任務：分離 production CLI 與 MMIS development tools
- 上層規格：2026-09-29 使用者核准的 development tools 分離需求
- 上層 Epic：MMIS 開發架構整理
- 上層 User Story：建立可持續的 MMIS 功能開發與依賴規範
- 分軌：後端
- 前置任務（dependsOn）：`MMIS-017`
- 狀態：完成
- 風險等級：中
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-29 明確要求執行）

## 目標

把四個部分功能的 executable interface 移到專用 development tools package，使正式 CLI 只呈現 production auto-link，同時維持所有 reusable implementation 原位且只有一份。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/cli.py`、四個正式 component modules、CLI／architecture tests、README、development workflow 與治理 artifacts。
- 既有模式：CLI handler 薄包裝正式 component；JSON stdout；安全遮蔽未預期錯誤；`tools/kanban/` 已建立 repo tooling 層。
- 假設：repository root 是 development tools 的執行工作目錄，專案已 editable install 或可由測試環境 import `mmis_connector`。
- 未知事項：外部是否有 wrapper 仍呼叫舊四個正式 CLI routes；README 將提供新指令。
- 允許變更的檔案：正式 CLI、`tools/mmis_development/`、相關 tests、README／workflow／context 與 MMIS-018 artifacts。
- 不得觸碰：正式 reusable components、auto-link business logic、SQLite schema／data、Live MMIS 資料、使用者既有 `Prompt.md` 修改。

## 需求

- 正式 CLI 只保留 auto-link production command。
- 四個 development tools 可獨立執行並直接 import 正式 components。
- 不複製 Maximo event、auth、parser、validation 或 domain implementation。
- 文件清楚區分 Production Features 與 Development／Diagnostic Tools。
- 架構測試禁止 production 反向依賴 tools／reference。

## 驗收標準

- `_commands()` 僅回傳 auto-link command；四個舊名稱由正式 CLI 拒絕。
- 四個 `python -m tools.mmis_development...` module 可 import、驗證參數，並以 mock 呼叫正確正式 class。
- Mutation tool 在文件中醒目警告，本次不做 Live execution。
- `src/mmis_connector/query_*.py`、Reader、Linker、auth、events、parser、Store、orchestrator 保持原位且 implementation 不變。
- 指定完整離線驗證通過，並記錄 pytest 前後數量。

## 實作備註

- 詳細決策見 `architecture-plan-MMIS-018.md`。
- 採 `tools/mmis_development/` 而非含連字號的 package 名，以支援標準 `python -m` 與測試 import。
- 共用 development CLI shell 僅處理 stdout／error，不提供 production 可 import API。

## 驗證契約

- 單元測試：正式 CLI command set、四個 development tools 的 arguments／mock invocation、架構 AST 邊界。
- 整合測試：既有 auto-link、Store、Query、Reader、Linker 全套離線回歸。
- E2E 測試：只做 module import／無網路錯誤路徑；不登入或 mutation。
- 型別檢查：專案未配置。
- Lint：`git diff --check` 與本任務檔 whitespace scan。
- Build：`python -m compileall -q src tests`、額外 compile development tools、`python -m pip check`。
- 螢幕截圖：不適用。
- 安全性檢查：敏感資料掃描、mutation 文件警告、production dependency scan。

## 完成證據

- 變更的檔案：production CLI、`tools/mmis_development/`、CLI／development／architecture tests、README、development workflow、context maps 與 MMIS-018 artifacts；正式 reusable modules 零變更。
- 執行過的指令：baseline／final pytest、20 項針對性測試、四個 module 無網路 import／argument execution、兩組 compileall、pip check、production CLI listing、diff／JSON／敏感資料檢查。
- 測試輸出：修改前 121 passed、3 skipped；修改後 128 passed、3 skipped；針對性 20 passed。
- 螢幕截圖：不適用。
- 已知限制：舊四個正式 CLI routes 是刻意 breaking interface change。
- 後續任務：評估 repository 外部 wrapper 是否需要切換至新 development module 指令。
