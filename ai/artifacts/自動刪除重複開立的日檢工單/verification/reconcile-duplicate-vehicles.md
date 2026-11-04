# 驗證報告

## 摘要

- 任務：補查重複日檢工單開單日期並標示取消候選
- 結果：部分通過；程式與 live 資料處理完成，指定里程碑與日期排序規則衝突，等待使用者決定優先要求
- 驗證者：Codex；另由獨立安全與正確性 reviewer 審查

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_unassigned_daily_inspection_work_orders.py -q` | 通過 | 7 項測試通過，含欄位順序、最新工單保留、查詢失敗、日期並列、重跑清除舊標記、快照競爭與非預期錯誤傳遞 |
| `python -m compileall -q tools/mmis_development/auto_delete_duplicate_daily_inspection_work_orders.py tests/test_unassigned_daily_inspection_work_orders.py` | 通過 | 目標程式與測試可編譯 |
| `git diff --check` | 通過 | 無空白錯誤 |
| `python -m pytest -q` | 部分通過 | 全套測試中 2 項 `tests/test_architecture.py` 失敗。其預期模組清單未列出既有 `daily_inspection/unassigned.py`，且預期 development tool 數 18、實際為 19；其餘測試通過。此變更沒有新增 production 模組或 development tool。 |
| `python -m tools.mmis_development.auto_delete_duplicate_daily_inspection_work_orders` | 通過 | Live MMIS 查詢 65 筆；1 個重複車組、補查 2 筆開單日期、標記 1 筆取消候選、無不完整或並列群組。 |
| SQLite 唯讀查詢 `PRAGMA table_info` 與 EMU929 rows | 通過 | 六欄順序正確；EMU929/115-1A-80361 為 2026/10/31 01:15 並標待工單取消；EMU929/115-1A-81454 為 2026/11/04 14:01 並保留。 |

## UI 證據

不適用。本任務只改 CLI 與 SQLite。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 新增的廣泛例外攔截可能隱藏程式錯誤 | 中 | 已修正為只攔截 `MMISClientError` 與日期格式 `ValueError`；新增測試確保其他錯誤繼續傳遞 |
| 使用者指定 115-1A-81454 待取消，但 live 日期顯示它是 EMU929 最新工單 | 產品驗收 | 等待使用者確認「保留最新」或指定工單里程碑何者優先 |

獨立 reviewer 未發現其他阻擋的安全或正確性問題。程式只使用 MMIS 唯讀 domain reader，SQL 值使用參數，沒有工單刪除或 MMIS 寫入。

## 殘留風險

- 在使用者確認衝突前，資料庫維持依開單日期規則計算的結果：保留 115-1A-81454，將 115-1A-80361 標記「待工單取消」。
- 完整測試套件仍有兩項既有架構盤點失敗；本任務未修改不相關的 production inventory 測試。
- 日期查詢失敗、日期無效或同一最新時間並列時，該車組不會被標記取消，命令會以非零結束碼回報。
