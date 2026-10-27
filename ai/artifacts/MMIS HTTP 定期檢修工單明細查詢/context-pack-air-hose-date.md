# 任務情境包：定期檢修工單空氣軟管日期

任務：新增依工作單查詢定期檢修工單「附表一」空氣軟管／安裝日期資料的 development CLI。

目標：輸入一個工作單號，讀取車組/車號，依車型選擇檢查項目關鍵字，輸出符合列的欄位 JSON；非 600、700、800 型回傳含「此工作單非支援的車型」的正常 JSON。

相關檔案：

- `src/mmis_connector/periodic_inspection/reader.py`
- `src/mmis_connector/parser.py`
- `src/mmis_connector/events.py`
- `tools/mmis_development/query_periodic_inspection_work_order_details.py`
- `tools/mmis_development/README.md`
- `tests/test_periodic_inspection_work_order_details.py`
- `tests/test_architecture.py`
- 指定 Recorder 的 `codex-summary.md`、`timeline.json`、`raw.har` 與最後 DOM。

既有模式：

- Development wrapper 只驗證 CLI 參數、建立 `MMISSession`、呼叫 production domain Reader，並使用 `run_json_tool` 輸出單一 JSON。
- Domain Reader 使用 `MaximoEventClient`，動態解析表格欄位及 ID，唯一且完全相符地定位工單，檢查頁面總筆數與分頁範圍。
- 工單明細的車組/車號由「車組/車號」label 與 input `for` 關聯讀取，不依賴錄製中的 input id。

假設：

- `records` 每筆只輸出「檢查項目」與「量測值」；其他欄位只用於來源表格解析，不輸出。
- 車型依車號 `EMU6xx`、`EMU7xx`、`EMU8xx` 前綴分類；其他值均以正常 JSON 回報不支援，不當成查詢錯誤。
- 無符合資料時回傳 `count: 0` 與空 `records`。
- 只讀 MMIS，不修改工單或回報值。

未知事項：

- 目前錄製僅涵蓋 800 型；600、700 型的實際資料筆數未由錄製證明，程式必須依 MMIS 分頁資訊讀取而不可寫死筆數。
- 600 型「安裝日期」欄位實際結果需以即時唯讀查詢或未來錄製確認。

允許變更的檔案：本 Epic 新增架構與任務產出物、`periodic_inspection/reader.py`、development wrapper、其測試、`tests/test_architecture.py`、`tools/mmis_development/README.md` 及 `ai/context/project-map.md`。

不得觸碰：登入憑證、Recorder 原始 evidence、其他 domain、production CLI routes、MMIS 資料。

驗證指令：`python -m pytest tests/test_periodic_inspection_work_order_details.py tests/test_architecture.py -q`、`python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development`；另以指定工作單執行即時唯讀 development CLI。

風險等級：高（網路存取與 MMIS session，但工作內容唯讀）。
