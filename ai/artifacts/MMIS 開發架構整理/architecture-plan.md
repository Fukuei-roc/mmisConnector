# 架構計畫

## 決策

- 保留全部正式 `src/mmis_connector/` module；它們是 auto-link 或單一操作 CLI 共用的 reusable components。
- 保留四個單一操作 CLI，作為 debugging、MMIS 行為確認、受控 Live 驗證與人工單筆操作入口。
- 不搬移檔案：repository 內沒有僅供開發、且目前混入 production runtime 的 Recorder script。
- 新增 development guide，集中記錄搜尋順序、已驗證 Maximo 能力、reference/evidence 規則與 dependency graph。
- 新增 import graph 離線測試，保護 application 不依賴 CLI 或 subprocess。

## API、資料與狀態契約

- 公開 Python API、CLI 名稱、參數、exit code 與 JSON stdout 不變。
- SQLite schema、批次清理、resume、逐筆 commit、`linking`、`link_error` 與摘要不變。
- MMIS event sequence、parser、auth 與網路行為不變。

## 風險與回滾

- 風險為低：只新增文件與靜態 import graph 測試，不修改 runtime code。
- 若 dependency graph 日後合理擴充，需同步更新 guide 與架構測試的 allowlist。
- 回滾可移除新增文件／測試並還原 README 與 context map，不涉及資料遷移。

## 驗證

- 針對性：架構、auto-link、store 與 CLI tests。
- 完整：`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`、`git diff --check`。
- 不執行任何 Live MMIS command。
