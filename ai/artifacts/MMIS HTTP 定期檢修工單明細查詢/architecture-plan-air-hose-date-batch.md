# 架構規劃：自動查詢空氣軟管日期

## 決策

以目標 `空氣軟管日期.xlsx` 作為量測資料與續跑狀態的單一持久檔案。可見工作表只保留七個使用者指定欄位，另以隱藏的 `_air_hose_progress` 工作表記錄來源快照、來源列、結果狀態、資料列數與輸出區塊摘要。每個工作單成功後，程式同時更新兩張工作表，再以同目錄暫存 XLSX 和 `os.replace` 原子替換目標檔案。

架構候選比較及獨立評分見 `.audit/auto-query-air-hose-dates/candidate-sheet.md` 與 `candidate-sqlite.md`。交叉審查選擇嵌入進度表，因為它符合現有 `periodic_inspection/workbook.py` 的逐筆原子儲存方式，也不需要讓使用者管理額外資料庫。SQLite checkpoint 被否決，因為要額外維護資料庫與活頁簿投影同步。

## 使用方式

```powershell
python -m tools.mmis_development.auto_query_air_hose_dates
```

CLI 使用固定來源與目標路徑，不接受參數。Domain operation 接受來源路徑、目標路徑和 reader factory，讓離線測試使用暫存活頁簿與 stub reader。

## 資料模型與模組

- 新增 `src/mmis_connector/periodic_inspection/air_hose_workbook.py`，負責驗證兩份活頁簿、建立來源快照、核對續跑 metadata、驗證 Reader 結果、逐筆更新、原子儲存與彙整批次結果。
- 新增 `tools/mmis_development/auto_query_air_hose_dates.py`，只負責拒絕 CLI 參數、載入 MMIS 設定、建立 `PeriodicInspectionWorkOrderDetailReader(MMISSession(config))` factory、輸出 UTF-8 JSON 摘要及結束碼。
- 新增 `tests/test_air_hose_workbook.py`，以真實暫存 XLSX 和 stub reader 驗證可見輸出、隱藏 checkpoint、重試及續跑。
- 不修改 `reader.py` 的單筆查詢，不從一個 development tool 用 subprocess 呼叫另一個 tool。

來源工作表 `最新檢修工單` 必須含四個指定欄位。每個非空來源列建立獨立來源紀錄，保存原始欄值，並以正規化後的欄值計算來源快照摘要。只要求「工作單」非空；其他來源欄位的空值照原樣輸出。重複工作單仍逐來源列查詢與回填；完成鍵使用來源 Excel 列號，避免把不同來源資料合併。不完整工作單或公式儲存格在登入 MMIS 前拒絕。

Reader 的成功結果需符合現有契約：工作單相符、`success` 為真、`supported` 為布林值、支援車型有有效 `車型`、`count` 等於 `records` 長度，且每筆記錄有字串「檢查項目」和「量測值」。車組/車號一律保留來源值，不用 Reader 的車號覆蓋或否決結果。結果錯誤只在摘要記錄例外類型，不保留錯誤原文。不支援車型與支援但零筆資料分別記錄為 `unsupported` 和 `empty`，都視為查詢完成，但不新增虛構的可見資料列。

每個 checkpoint 記錄來源列號、工作單、來源列摘要、結果狀態、車型、資料筆數及 SHA-256。重跑只有在來源快照相同，且所有完成區塊的筆數和摘要都與可見工作表相符時才略過該列。任何來源變更、未知 checkpoint 版本、額外的未追蹤輸出列或摘要不符都停止處理，不自動覆寫資料。

如果早期來源列曾失敗而後續列已完成，程式將依已驗證的可見資料區塊和新結果重建七欄工作表，排序依來源列號。重建後重新計算每筆 checkpoint 的資料筆數和摘要，再一同原子保存。這讓續跑後的輸出仍與來源順序一致。

## 執行與錯誤處理

程式先完整驗證來源與目標，再建立 MMIS session。它依來源順序查詢未完成工作單，每筆最多嘗試三次；發生 `MMISClientError` 後丟棄 Reader，下一次嘗試建立新 session。三次失敗後保留該列為未完成並繼續處理其他工作單。批次摘要列出失敗、不支援與零筆結果的來源列和工作單。摘要中的不支援及零筆資料涵蓋本次目標活頁簿的完整已完成狀態，續跑時也會包含先前完成的來源列。若仍有失敗則以非零狀態結束。

每筆成功結果及其 checkpoint 在同一 XLSX 暫存檔中保存，完成後才 `os.replace` 目標檔。若程序在查詢期間終止，該列沒有進度記錄，下次會重查。若原子替換失敗，程式停止，原目標檔保留先前完整內容。零筆與不支援結果也保存 checkpoint，避免續跑時重複查詢。

輸出路徑使用作業系統 advisory lock，避免兩個程序同時讀寫同一活頁簿。鎖由程序持有的檔案控制代碼管理，程序結束或崩潰後由作業系統釋放。目標檔案在 Excel 開啟時若無法替換，回報錯誤並保留上一個有效版本。

## 安全性與風險

- MMIS 只使用既有唯讀查詢 Reader，不新增儲存或勾稽事件。
- 憑證只由既有 `.env` 與 `MMISConfig` 載入。摘要與錯誤不輸出 cookie、token 或 session 資料。
- 驗證工作表、欄名、公式儲存格及來源值。從 MMIS 取得的字串以文字格式寫入，避免以公式執行。
- 目標工作簿和隱藏進度表均位於使用者指定的輸出檔；不新增資料庫或其他業務資料副本。
- 風險為高，因為批次同時使用 MMIS 網路 session 並改寫本機活頁簿。實作後需要安全、架構與測試審查。

## 驗證與回復

- 離線測試使用臨時活頁簿與 stub reader，涵蓋欄位對應、變動筆數、零筆、不支援、三次重試、失敗後繼續、重跑略過、來源變更、重複工作單各自處理、checkpoint 損毀、原子替換失敗及併發鎖。
- 驗證指令為 `python -m pytest tests/test_air_hose_workbook.py tests/test_periodic_inspection_workbook.py tests/test_architecture.py -q`、`python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development` 和 `git diff --check`。
- 離線檢查通過及審查完成後，再用指定活頁簿和 MMIS session 執行批次。檢查實際可見資料列和隱藏 checkpoint；有失敗時保留可續跑狀態。
- 回復新增 module、tool、測試與文件即可。目標 XLSX 以原子替換更新；實際執行前保留其副本供人工回復。

## 審查記錄

- 架構候選 A（隱藏進度工作表）對中斷續查、輸出一致性、簡潔性、重複執行安全和實作範圍評分為 5、5、4、4、4。
- 架構候選 B（SQLite checkpoint）同項評分為 5、4、2、2、2。
- 獨立交叉審查建議採用候選 A，並加入零筆與不支援的不同完成狀態、嚴格回應驗證和失敗後繼續處理。後續測試審查依「逐一處理來源每一筆」要求確認重複工作單也要分列查詢與保存。
