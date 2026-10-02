# AI-Ready 任務卡

## Metadata

- 任務：整合故障通報完整唯讀查詢
- 上層規格：`ai/artifacts/MMIS HTTP 故障通報整合查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 故障通報整合查詢
- 上層 User Story：整合查詢與條件式 ATP 分析
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002（專案設置已完成）
- 狀態：完成（使用者以新增基本資料需求承接本整合命令）
- 風險等級：高（既有認證及內網唯讀查詢）
- Agent owner：Codex
- 人工核准者：使用者於 2026-10-02 明確確認規格並要求實作

## 目標

以一個命令、一個通報號輸出六個頂層項目的單一 JSON。

## 情境包（Context Pack）

- 相關檔案：四個 `fault_notices` reader、共用 parser、`tools/mmis_development/_support.py`。
- 既有模式：精確通報號定位、`MMISSession`、Maximo event、語意欄位解析、分頁與去重。
- 假設：兩類工單為獨立頂層陣列，未勾選 ATP 時分析為 `null`。
- 未知事項：無阻擋事項。
- 允許變更的檔案：新 reader／工具／測試／治理產出物；必要的工單 reader 共用方法及架構 inventory。
- 不得觸碰：`Prompt.md`、遠端寫入流程、既有獨立工具輸出契約。

## 需求

- 一次登入、精確找到唯一通報；在同一明細查 ATP 與兩種工單、五欄故障分析及條件式三欄 ATP 分析。
- 錯誤時非零退出並輸出 JSON；不輸出部分成功資料。

## 驗收標準

- 六個頂層項目名稱及型別符合規格。
- 兩種工單可各自為空、跨頁；既有去重與 CA 篩選維持不變。
- ATP 勾選與未勾選皆可成功；格式錯誤在登入前拒絕。
- 四個既有工具與完整測試套件無回歸。

## 實作備註

- 重用現有 readers 的分頁迴圈，以 `read_records` 讀取已開啟的追蹤頁籤。
- 不透過 subprocess 呼叫既有工具。

## 驗證契約

- 單元測試：整合查詢兩條 ATP 路徑及兩張表；格式驗證。
- 整合測試：既有工單與分析測試；完整 pytest。
- E2E 測試：兩筆授權通報的唯讀 live 查詢。
- 型別檢查：專案未配置獨立 typecheck。
- Lint：`git diff --check`。
- Build：`python -m compileall -q src tools`。
- 螢幕截圖：無 UI 變更，不適用。
- 安全性檢查：輸入驗證、憑證與輸出邊界、唯讀事件、無結果落盤。

## 完成證據

- 變更的檔案：見 `verification/MMIS-027.md`。
- 執行過的指令與測試輸出：見 `verification/MMIS-027.md`。
- 螢幕截圖：不適用。
- 已知限制：live 驗證只涵蓋各一筆 ATP 與非 ATP 通報；多頁情境以離線測試驗證。
- 後續任務：待人工驗收。
