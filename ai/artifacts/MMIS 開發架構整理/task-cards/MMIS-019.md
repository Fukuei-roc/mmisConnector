# AI-Ready 任務卡

## Metadata

- 任務：稽核 production source 是否仍含 development-only implementation
- 上層規格：2026-09-29 使用者核准的逐檔 production dependency 稽核需求
- 上層 Epic：MMIS 開發架構整理
- 上層 User Story：建立可持續的 MMIS 功能開發與依賴規範
- 分軌：不適用
- 前置任務（dependsOn）：`MMIS-018`
- 狀態：完成
- 風險等級：低
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-29 明確要求執行）

## 目標

逐檔與逐符號驗證 `src/mmis_connector/` 的 Production 必要性，只移動真正 development-only code，並以持久性 inventory 說明保留或移動理由。

## 情境包（Context Pack）

- 相關檔案：全部 `src/mmis_connector/*.py`、四個 development tools、architecture／public API／功能 tests、README 與 context maps。
- 既有模式：auto-link 以 factory 直接建構三個 service；Linker 再建構 DetailReader；共享 transport、parser 與 session。
- 假設：只有無 Production 執行路徑、無正式 reusable 價值且僅 tools 使用的 implementation 才可移出。
- 未知事項：無；import、建構與方法呼叫皆可由 source／tests 靜態驗證。
- 允許變更的檔案：source inventory 文件、README／workflow／搜尋指南、architecture test 與本卡 artifacts。
- 不得觸碰：已確認為 Production dependency 的 Query／Reader／Linker、auth、events、parser、Store、orchestrator、Live MMIS 資料與使用者 `Prompt.md`。

## 需求

- 完整分類每個 production package module。
- 對四個歷史功能 module 回答 direct／indirect dependency、Production consumer、tool consumer 與移動可行性。
- 審核 mixed CLI／formatting／standalone code 與 `__init__.py` exports。
- 若沒有 C 類 module，不做錯誤搬移；明確記錄結論。

## 驗收標準

- Inventory 覆蓋目前全部 12 個 `.py`。
- Architecture test 保證每個 source module 都屬於 auto-link closure 或正式 entry/public package files。
- Production 不 import tools，tools 仍 import正式 components。
- 完整離線驗證通過；不執行 Live mutation。

## 實作備註

- 本次證據顯示沒有可搬 module，因此 runtime source 預期零變更。
- `DetailReader.run()` 是 domain Reader API，不是 CLI wrapper；Production Linker 仍依賴同 class 的 `open_detail()` 與 schema constants。

## 驗證契約

- 單元測試：architecture classification、auto-link、public API、development tools。
- 整合測試：完整 pytest。
- E2E 測試：不執行 Live MMIS。
- 型別檢查：專案未配置。
- Lint：`git diff --check` 與 task-file whitespace scan。
- Build：兩組 compileall、pip check。
- 螢幕截圖：不適用。
- 安全性檢查：production import boundary 與敏感資料掃描。

## 完成證據

- 變更的檔案：新增 production source inventory，更新 README／workflow／搜尋指南、新增一項 architecture classification test 與 MMIS-019 治理／知識回寫 artifacts；runtime source 零變更。
- 執行過的指令：逐檔與符號 usage 搜尋、49 項針對性 pytest、完整 pytest、兩組 compileall、pip check、diff check、敏感資料與 import boundary scans、MMIS knowledge update script。
- 測試輸出：修改前 128 passed、3 skipped；修改後 129 passed、3 skipped。
- 螢幕截圖：不適用。
- 已知限制：module-level closure 無法代表每個方法當前都由 auto-link 呼叫，故另做 mixed-code domain responsibility 審核。
- 後續任務：若未來新增 source module，必須同步分類 inventory 與 architecture allowlist；若要重新命名 services，另立 public API migration task。
