# AI-Ready 任務卡

## Metadata

- 任務：HTTP 遍歷 ATP 選項並原子匯出
- 上層規格：`../feature-spec.md`
- 上層 Epic：MMIS HTTP ATP故障分析選項匯出
- 上層 User Story：ATP 選項匯出
- 分軌：後端
- 前置任務（dependsOn）：無
- 狀態：完成
- 風險等級：高
- Agent owner：Codex
- 人工核准者：使用者 2026-10-16 任務書

## 目標

提供可執行 HTTP CLI，產生完整 ATP 三層選項 JSON。

## 情境包（Context Pack）

- 相關檔案：`auth.py`、`events.py`、`parser.py`、`fault_notices/reader.py`、錄製 `raw.har`、Development README。
- 既有模式：`MMISSession`、`MaximoEventClient`、Maximo table/page parser、薄型 tool wrapper。
- 假設：lookup `click` 與選列只更改當前未儲存 UI 狀態；錄製無儲存事件。
- 未知事項：其他分支的實際選項及空清單，須由 live 遍歷確認。
- 允許變更的檔案：ATP 新 domain module、tool、測試、fixture、Development README、架構測試與本產出物。
- 不得觸碰：Production CLI、其他 Development Tools、原始 HAR。

## 需求

- 完整跨頁；父子分支隔離；部分錯誤不得覆蓋完整成果；不得送業務寫入事件。

## 驗收標準

- 完成狀態、統計與 JSON 內容一致；錯誤分支標示 null 與路徑。

## 實作備註

- 第一層由 lookup 直接讀取；後兩層透過選取上層列建立相依關係。
- 先寫同目錄暫存檔，再 `os.replace`。

## 驗證契約

- 單元測試：`python -m pytest tests/test_atp_options.py -q`
- 整合測試：`python -m pytest -q`
- E2E 測試：`python -m tools.mmis_development.export_atp_fault_analysis_options 1151012-36`
- 型別檢查：專案未提供。
- Lint：`git diff --check`；ruff 未安裝。
- Build：Python 模組可匯入。
- 螢幕截圖：不適用。
- 安全性檢查：唯讀 event allowlist、同源請求、token 不輸出。

## 完成證據

- 變更的檔案：見 verification 報告及 git diff。
- 執行過的指令：見 verification 報告。
- 測試輸出：pytest 通過，live completed。
- 螢幕截圖：不適用。
- 已知限制：錄製只提供一條完整分支；跨頁以現有 Maximo 通用控制項處理。
- 後續任務：MMIS 選項變更時重新匯出。
