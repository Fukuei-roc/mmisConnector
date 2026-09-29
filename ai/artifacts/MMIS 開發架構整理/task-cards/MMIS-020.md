# AI-Ready 任務卡

## Metadata

- 任務：依 domain responsibility 重整 Production modules
- 上層規格：2026-09-29 使用者核准的 Production module rename／move 需求
- 上層 Epic：MMIS 開發架構整理
- 上層 User Story：建立可持續的 MMIS 功能開發與依賴規範
- 分軌：不適用
- 前置任務（dependsOn）：`MMIS-019`
- 狀態：完成
- 風險等級：中
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-29 明確要求執行）

## 目標

將六個以早期操作命名的 Production modules 實體移至 `fault_notices/`、`daily_inspection/` 與 `auto_link/` domain packages，僅更新 imports、測試與文件，不改變任何 runtime 行為或外部命令契約。

## 情境包（Context Pack）

- 相關檔案：`src/mmis_connector/`、全部引用舊 module path 的 tests／tools／維護中文件、architecture tests、public API tests。
- 既有模式：root package-level exports 是正式 public API；CLI 與 development tools 是穩定 executable contracts；Maximo protocol 集中在既有 Query／Reader／Linker 與 transport。
- 假設：舊 internal module path 沒有被文件承諾為 public API，不建立 forwarding shim；歷史治理 artifacts 保留當時路徑作為不可改寫的紀錄。
- 未知事項：repository 外可能有人直接 import 舊 internal path，但無文件、package exports 或 packaging metadata 證據支持該 compatibility contract。
- 允許變更的檔案：六個 Production module 的位置與內部 imports、三個新 package `__init__.py`、root `__init__.py`、CLI imports、tests、development tools imports、README／development docs／context maps、MMIS-020 artifacts 與看板卡。
- 不得觸碰：Maximo payload／event ordering、auth／events／parser 實作、class 名稱、business logic、CLI／tool 名稱與參數、JSON／exit-code contract、Live MMIS 資料、使用者 `Prompt.md`。

## 需求

- 使用實體 rename／move，Production implementation 維持單一份。
- 保持 root `mmis_connector` 現有 `__all__` public API。
- 更新全部 active code imports、patch targets、architecture assertions 與 current documentation。
- 移除六個舊 internal module files，不留 compatibility shim。
- 不執行任何 Live MMIS command。

## 驗收標準

- Source tree 依 `fault_notices/query.py`、`daily_inspection/{query,reader,linker}.py`、`auto_link/{orchestrator,store}.py` 組織。
- Production CLI 與四個 development tool command／arguments／JSON／exit code 不變。
- Root package-level exports 與修改前完全一致。
- Architecture tests 支援巢狀 package，保護 exact dependency closure、inventory 與 Production→tools 禁止邊界。
- 修改後完整測試不低於 baseline `129 passed, 3 skipped`，且所有 compile／dependency／diff checks 通過或已說明既有非任務問題。

## 實作備註

- Architecture：domain packages 只負責 source organization；不新增 service abstraction，也不搬動 shared `auth.py`、`events.py`、`parser.py`。
- API／資料契約：無變更；root `__all__` 維持原集合，internal module paths 更新。
- 遷移／回滾：Git rename 可直接反向搬回；無資料、schema 或 MMIS migration。
- 安全性：不修改憑證、session、HTTP 或 mutation 邊界；禁止 Live 驗證。

## 驗證契約

- 單元測試：各 Query／Reader／Linker／Store／Orchestrator、CLI、public API、development tools、architecture。
- 整合測試：完整 `python -m pytest`。
- E2E 測試：不執行 Live MMIS；CLI dispatch 使用既有 mock tests。
- 型別檢查：專案未配置。
- Lint：`git diff --check`，並排除既有使用者 `Prompt.md` 後確認本任務 diff。
- Build：`compileall`（src/tests 與 development tools）、`pip check`。
- 螢幕截圖：不適用，無 UI。
- 安全性檢查：Production import closure、禁止 tools imports、敏感資訊與 subprocess 靜態掃描。

## 完成證據

- 變更的檔案：六個 Production modules 實體搬移；新增三個 domain package `__init__.py`；更新 root API／CLI／tools／tests／current docs／context maps 與 MMIS-020 artifacts。
- 執行過的指令：修改前與修改後完整 pytest、58 項針對性 pytest、兩組 compileall、pip check、兩組 diff check、package／CLI／tools import smoke、old-path／forbidden-import scans、六個 moved modules 的 non-import AST comparison、MMIS knowledge update script。
- 測試輸出：修改前 `129 passed, 3 skipped`；修改後 `130 passed, 3 skipped`；增加 1 項 package public API 精確集合測試。
- 螢幕截圖：不適用。
- 已知限制：repository 外若曾直接 import 未承諾的舊 internal path，會需要改用 package-level public API 或新 domain path。
- 後續任務：repository 外若有直接使用舊 internal module path 的 consumer，改用穩定 root package API 或新 domain path；目前沒有此 compatibility requirement 的證據。
