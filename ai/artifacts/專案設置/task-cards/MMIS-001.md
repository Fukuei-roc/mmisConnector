# AI-Ready 任務卡

## Metadata

- 任務：建立 Python 技術骨架
- 上層 Epic：專案設置
- 上層 User Story：Python 技術骨架
- 分軌：後端
- 前置任務（dependsOn）：無
- 狀態：完成
- 風險等級：低
- Agent owner：Codex
- 人工核准者：不適用（Epic 0 必要項）

## 目標

建立可安裝、可測試、可由 module 執行的 Python 3.11 CLI 專案。

## 驗收標準

- `python -m pip install -e ".[test]"` 成功。
- `python -m pytest` 可執行。
- 套件以 `src/` layout 組織。

## 驗證契約

- Build：editable install。
- 測試：pytest。
- 語法：compileall。
