# AI-Ready 任務卡

## Metadata

- 任務：新增定期檢修工單空氣軟管日期查詢 development tool。
- 上層規格：`../feature-spec.md`（新增空氣軟管日期需求）。
- 上層 Epic：MMIS HTTP 定期檢修工單明細查詢。
- 上層 User Story：依工作單查詢車型對應的附表一檢查項目。
- 分軌：後端。
- 前置任務（dependsOn）：無。
- 狀態：審查中。
- 風險等級：高（唯讀 MMIS 網路查詢）。
- Agent owner：Codex。
- 人工核准者：使用者已於 2026-10-27 提供明確需求並要求實作。

## 目標

新增 `python -m tools.mmis_development.query_periodic_inspection_work_order_air_hose_date <工作單>`，依工單車型過濾附表一並輸出各筆的「檢查項目」與「量測值」。

## 情境包（Context Pack）

- 相關檔案：見 [任務情境包](../context-pack-air-hose-date.md)。
- 既有模式：HTTP-only、`MaximoEventClient`、動態表頭解析、`run_json_tool`。
- 假設：`EMU6xx/7xx/8xx` 按 EMU 後第一位車號數字分類；每筆只輸出「檢查項目」與「量測值」。
- 未知事項：指定錄製只涵蓋 800 型；600 與 700 型資料數量及 live 結果待實際查詢。
- 允許變更的檔案：情境包中列出的範圍。
- 不得觸碰：憑證、Recorder evidence、其他 domain 或 MMIS 資料。

## 需求

- 接受且只接受一個非空工作單號。
- 唯一定位工作單後，依「車組/車號」欄位解析車型。
- 600 型使用「安裝日期」；700、800 型使用「空氣軟管」。
- 依 label「檢修回報」及「附表一」定位頁籤，開啟附表一過濾器，依動態「檢查項目」欄輸入關鍵字並送出 filterrows。
- 讀取所有符合頁面中的附表一資料列，每筆只輸出「檢查項目」與「量測值」。
- 不支援車型輸出含「此工作單非支援的車型」的 JSON，exit code 為 0。
- 所有 Maximo request 僅唯讀，不寫入資料。

## 驗收標準

- 800 型錄製 DOM 可解析成 13 筆資料，包含 9 個資料欄位（不含 Maximo 的空白列選擇欄）。
- 600、700、800 型車號依 registry 對應正確關鍵字；不支援值正常回傳 JSON。
- 工作單找不到或結果不唯一、表格或分頁不一致時，沿用既有安全錯誤 JSON 契約。
- CLI stdout 僅有 JSON，參數錯誤由共用 wrapper 回傳錯誤 JSON。
- 既有 periodic inspection details 查詢行為維持通過其測試。

## 實作備註

- 在 periodic inspection Reader 中重用並抽出唯一工作單明細開啟步驟，避免重複事件流程。
- 用車型設定表集中表達車號前綴與過濾關鍵字。
- 使用共用 parser 和 page-info 驗證，不使用固定 DOM IDs 或固定總筆數。
- 在目前附表一 filter 狀態不明時，從動態 toolbar 控制辨識過濾器並開啟。

## 驗證契約

- 單元測試：車型分類、unsupported JSON、動態 filter target、限定輸出欄位與跨頁／零筆資料。
- 整合測試：Recorder DOM 的附表一表格解析與 13 筆結果。
- E2E 測試：以指定工單執行 development CLI 的即時唯讀查詢（有可用 MMIS session 時）。
- 型別檢查：不適用，專案未使用獨立 type checker。
- Lint：不適用，專案未設定獨立 lint 指令。
- Build：`python -m compileall`。
- 螢幕截圖：不適用，CLI 無 UI。
- 安全性檢查：`ai/checklists/security-checklist.md`，確認唯讀、未寫入 secret、錯誤訊息不洩漏 session。

## 完成證據

- 變更的檔案：`src/mmis_connector/periodic_inspection/reader.py`、`tools/mmis_development/query_periodic_inspection_work_order_air_hose_date.py`、`tests/test_periodic_inspection_air_hose_date.py`、`tests/test_architecture.py`、`tools/mmis_development/README.md`、`ai/context/project-map.md` 及本 Epic 規格／架構／情境／驗證產出物。
- 執行過的指令：`python -m pytest -q`、`python -m compileall -q src tools/mmis_development`、`git diff --check`、指定工作單即時唯讀 CLI 查詢。
- 測試輸出：全套 pytest 通過至 100%；compileall 與 diff check exit 0。即時 800 型查詢成功回傳 13 筆。
- 螢幕截圖：不適用，CLI 無 UI。
- 已知限制：目前 Recorder 與 live 查詢只驗證 800 型；600／700 型以使用者給定映射和離線測試驗證。零筆回應使用模擬 Maximo 頁面資訊。
- 後續任務：如日後車型增加，再更新車型 registry 與對應錄製證據。
