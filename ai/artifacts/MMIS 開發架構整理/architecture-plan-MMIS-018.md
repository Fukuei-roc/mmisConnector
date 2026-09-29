# MMIS-018 架構計畫

## 決策

- 新增 `tools/mmis_development/` Python package，與既有 `tools/kanban/` 同層。
- 四個 development tool 各自提供 `main(argv)` 與 `python -m` 入口，只負責參數、建立 `MMISSession`、呼叫正式 reusable component、JSON stdout／exit code。
- 共用 JSON/error shell 放在 development package 的 `_support.py`，不進入 production package。
- 正式 `src/mmis_connector/cli.py` 僅保留 auto-link production command。
- 不移動或修改 Query、Reader、Linker、parser、auth、events、Store 或 orchestrator implementation。

## 契約

- Production command 保持 `auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders`、參數、JSON 與 exit code 不變。
- 原四個 command 不再由 `python -m mmis_connector` dispatch；改由 `python -m tools.mmis_development.<module>` 執行。
- Development tools 成功與失敗仍輸出 JSON；未預期例外仍遮蔽細節。
- 單筆故障通報勾稽工具仍可能 mutation，README 必須明確警示，且本次不做 Live 驗證。

## 風險與回滾

- 風險中等：刻意移除四個既有正式 CLI routes，可能影響既有人工指令或 wrapper。
- 底層 Python API 與 production behavior 不變；回滾只需恢復 CLI handlers 並移除 tools package。
- 不涉及資料 schema、migration 或 Live MMIS 寫入。

## 驗證

- Development tools：import、argument validation、mock component invocation、JSON errors。
- Production CLI：command set 僅含 auto-link；舊四個名稱明確拒絕。
- Architecture：所有 production modules 不 import `tools`／development／reference；development tools import 正式 `mmis_connector` components。
- 完整離線 pytest、compileall、pip check 與 diff check。
