# AI-Ready 任務卡

## Metadata

- 任務：將啟動指令改為可擴充的功能子命令
- 上層規格：`feature-spec.md`
- 上層 Epic：MMIS HTTP 未處理通報擷取
- 上層 User Story：查詢並輸出故障通報 JSON
- 分軌：後端
- 前置任務（dependsOn）：MMIS-005
- 狀態：完成（2026-09-21）
- 風險等級：低
- Agent owner：Codex
- 人工核准者：專案使用者

## 目標

讓單一 `mmis-connector` 主入口可透過具體功能子命令擴充，不再以無參數命令隱含執行某一功能。

## 情境包（Context Pack）

- 相關檔案：`cli.py`、`__main__.py`、`pyproject.toml`、README、project map
- 既有模式：CLI 所有成功與失敗結果皆輸出 JSON
- 假設：目前唯一功能是查詢本段未處理通報
- 未知事項：無
- 允許變更的檔案：CLI、CLI 測試、README、治理文件
- 不得觸碰：登入、HTTP event sequence、parser、結果 JSON 契約

## 需求

- 新指令為 `python -m mmis_connector query-unprocessed-fault-notices`。
- console script 指令為 `mmis-connector query-unprocessed-fault-notices`。
- 缺少或未知子命令時不得連線 MMIS，並以 exit 1 輸出安全 JSON。
- README 記錄未來子命令命名範例。

## 驗收標準

- 無參數及未知命令均回傳可解析錯誤 JSON。
- 正確子命令會分派到 `UnprocessedFaultNoticeQuery`。
- 完整測試通過。

## 驗證契約

- 單元測試：命令分派、缺少命令、未知命令。
- 回歸測試：完整 pytest。
- 語法：compileall。
- 文件搜尋：目前啟動範例全部包含子命令。
