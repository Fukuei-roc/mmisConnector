# AI-Ready 任務卡

- 任務：MMIS-049 完成同步後匯出 XLSX
- 上層 Epic：自動處理 A-B 級未結案故障通報
- User Story：完成同步後匯出 XLSX
- 狀態：完成；人工核准：使用者 2026-10-20 明確規格
- 風險：高（本機資料庫同步與 OneDrive 檔案輸出）
- 前置任務：MMIS-048（完成）

## 情境包

- 相關檔案：自動處理 Development Tool、相關測試、`.env.example`、`pyproject.toml`、Development Tool README。
- 既有模式：SQLite 全量快照及逐筆明細檢查；JSON stdout 與非零失敗碼；dotenv 讀專案 `.env`。
- 允許變更：Development Tool、XLSX helper、測試、依賴與環境範例、工具 README、本 Epic 治理產出物。
- 不得觸碰：正式 MMIS CLI、HTTP event、認證、資料庫 schema、根 README、正式 SQLite 與 OneDrive 測試檔案。
- 假設：現有 `partial_success` 不符合完整同步成功，故不匯出。
- 驗證：mock MMIS + 暫存 SQLite/XLSX、openpyxl 讀回、完整 pytest、compileall、pip check、diff check。
- 情境預算：只讀與同步、匯出、環境載入及測試相關檔案，跳過無關 Production/前端。

## 驗收標準

- 原指令不產生 XLSX；新旗標先執行完整同步，成功後唯讀資料庫匯出本次資料。
- 15 欄順序、NULL、布林、字型、對齊、欄寬、長文字與公式文字安全符合規格。
- 同名流水號排他建立，不覆蓋；匯出失敗保留已提交 SQLite，清除不完整檔案。
- `.env`／`.env.example` 正確設定，缺失或不存在的輸出資料夾明確報錯。
- 不執行 Live MMIS 或正式 OneDrive 匯出。
