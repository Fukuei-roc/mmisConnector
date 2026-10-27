# 驗證報告

## 摘要

- 任務：最新定期檢修工單新增 `2A,3A` 檢修級別條件。
- 結果：通過。
- 驗證者：Codex；獨立正確性、安全性與架構審查已核准。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| 變更前 `python -m tools.mmis_development.query_latest_periodic_inspection_work_order 813` | 成功重現問題 | 回傳 `EMU813 / TR / 115-3A-68700-003 / 2026/09/18`。 |
| 變更前 `python -m pytest tests/test_query_latest_periodic_inspection_work_order.py -q` | 1 項失敗 | 錄製檔已更新為 `813`，舊測試仍期待 `701／17 筆`；實際為 19 筆。 |
| `python -m pytest tests/test_query_latest_periodic_inspection_work_order.py -q` | 13 項通過 | 涵蓋四條件事件順序、跨頁、錯誤級別，及錄製 HAR 的 `813／19 筆`、車號與級別分布。 |
| `python -m pytest -q` | 通過，exit 0 | 全套測試；其他功能的既有略過案例保留。 |
| `python -m tools.mmis_development.query_latest_periodic_inspection_work_order 813` | 通過，exit 0 | 即時唯讀查詢輸出 `EMU813 / 3A / 115-3A-68700-001 / 2026/09/14`，JSON 恰有四個指定欄位。 |
| `python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development/query_latest_periodic_inspection_work_order.py` | 通過，exit 0 | 無輸出。 |
| `git diff --check HEAD~1 HEAD` | 通過，exit 0 | 無空白錯誤。 |

## UI 證據

本任務沒有 UI 變更。錄製截圖與 HAR 只在本機對照，沒有複製進專案。

## 審查與殘留風險

- 程式沿用既有 `MMISSession`、Maximo event 與四欄 JSON 契約。沒有新增憑證儲存、檔案輸出或 MMIS 寫入。
- 獨立審查確認錄製的四項事件順序與程式一致，並核准此變更。錄製測試已補逐筆車號及級別檢查；錄製回應中的檢修單位與工單狀態編碼不可靠，以事件請求及即時查詢確認。
- 即時資料可能在錄製後變更；本次驗證以查詢當下的完整結果選出最新一筆。
- 後續若 MMIS 改變過濾欄位或級別代碼，需以新錄製檔更新事件與回應測試。
