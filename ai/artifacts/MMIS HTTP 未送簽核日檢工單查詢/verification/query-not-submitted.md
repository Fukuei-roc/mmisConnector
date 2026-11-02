# 驗證報告

## 摘要

- 任務：查詢未送簽核的日檢工單
- 結果：實作與自動驗證通過，待人工驗收
- 驗證者：Codex；另有獨立唯讀審查 agent

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest -o addopts='' -q` | exit 0 | 547 passed，44 skipped；跳過項目多為缺少本機錄製 fixture 的既有測試。 |
| `python -m compileall -q src/mmis_connector/daily_inspection/not_submitted.py tools/mmis_development/query_daily_inspection_work_orders_not_submitted_for_approval.py` | exit 0 | 語法檢查通過。 |
| `git diff --check` | exit 0 | 無空白格式錯誤。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval` | exit 0 | 2026/11/02 Live 唯讀查詢回傳 `success: true`、`count: 1`，工作單 `115-1A-80870`，14 欄完整。 |
| `python -m tools.mmis_development.query_daily_inspection_work_orders_not_submitted_for_approval unexpected` | exit 1 | 輸出參數錯誤 JSON。 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| MMIS 可能回傳未套用過濾條件的舊清單。 | 中 | 已加入逐列檢修段、工作單狀態與檢修日期核對及測試。 |
| 身分驗證、憑證與網路邊界。 | 高風險關卡 | 沿用既有 `MMISSession` 與 event client。無新憑證儲存、無新增外部 URL、唯讀 event。獨立審查未發現安全性問題。 |

## 限制與後續

- 錄製檔與 Live 查詢均只有 1 筆。31 筆跨頁行為由合成 Maximo 回應驗證，尚無真實多頁 Live 樣本。
- 查詢語義依 2026/11/02 錄製的三個過濾條件。MMIS 畫面若更動欄名或分頁控制項，查詢會報錯。
- 沒有 UI 變更，螢幕截圖不適用。專案沒有獨立 lint、型別檢查與 build 指令。
- 後續由使用者驗收結果欄位與業務定義；有多頁 Live 樣本時可再驗證實際分頁。
