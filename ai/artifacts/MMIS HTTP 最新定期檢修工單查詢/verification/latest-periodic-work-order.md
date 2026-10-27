# 驗證報告

## 摘要

- 任務：查詢最新定期檢修工單。
- 結果：通過。
- 驗證者：Codex；獨立程式審查已核准。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_query_latest_periodic_inspection_work_order.py -q` | 通過，12 個測試 | 涵蓋跨頁、日期排序、同日、空結果、錯誤、車號碰撞、CLI JSON，以及本機錄製 HAR 解析。 |
| `python -m pytest -q` | 通過，exit 0 | 全套測試；既有與本機缺少錄製檔的案例依標記略過。 |
| `python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development/query_latest_periodic_inspection_work_order.py` | 通過，exit 0 | 無輸出。 |
| `python -m tools.mmis_development.query_latest_periodic_inspection_work_order 701` | 通過，exit 0 | 即時 MMIS 唯讀查詢輸出 `EMU701`、`2A`、`115-2A-74357-001`、`2026/10/15`，恰有四個指定欄位。 |
| `git diff --check` | 通過，exit 0 | 無空白錯誤。 |

## UI 證據

本指令沒有 UI 變更。錄製截圖僅用於確認欄位與結果；沒有複製到專案。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| `701` 的 MMIS 模糊篩選可能含 `EMU1701`，導致選錯車組。 | 中 | 已加入車號邊界比對與混合車組測試。 |
| 非目標車組欄位不完整時可能阻斷有效結果。 | 中 | 已先排除非目標車組，再檢查命中列的完整性。 |
| 從日檢模組借用輸入驗證造成跨領域依賴。 | 低 | 已改為定期檢修查詢模組內的輸入邊界驗證。 |
| 新程式、測試、認證及資料輸出安全審查。 | 無阻擋項 | 獨立審查核准；沒有新增憑證儲存或納入敏感 HAR。 |

## 殘留風險與後續

- 數字車號在其他複合標籤中的邊界語意尚無錄製樣本；目前已驗證 `701` 命中 `EMU701` 且排除 `EMU1701`。若 MMIS 出現其他命名格式，需以新的錄製資料更新比對測試。
- MMIS 為即時資料；工單內容可能在錄製與再次查詢後變動。功能在查詢當下依完整結果選最新一筆。
