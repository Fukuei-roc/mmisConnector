# 驗證報告

## 摘要

- 任務：MMIS-029 臨時檢修工單維修程序概況查詢
- 結果：通過，待人工驗收
- 驗證者：Codex

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_temporary_repair_procedure.py -q` | 通過 | 錄製 HAR 重放、空清單、表格辨識、參數檢查 |
| `python -m pytest -q` | 通過 | 全套測試；既有部分測試依環境跳過 |
| `python -m compileall -q src tools/mmis_development tests` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | `No broken requirements found.` |
| `git diff --check` | 通過 | 無 whitespace 錯誤 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C2-41266` | 通過 | 原錄製 HAR 有 2 筆；目前 live JSON 有 3 筆，每筆 9 欄 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C1-41264` | 通過 | 修正後 live JSON `count=1`，逐列車號 `EMA815`，多行維修程序保留 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C1-41264` | 通過 | 故障現象為 `其它問題：BECU單元故障(#101、#102、#139)` |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C2-41266` | 通過 | 目前 3 筆；第一筆 `其它問題：Batk2不動作`，第二筆維持原值，第三筆三種其它補充皆正確 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_maintenance_procedure_summary 115-C2-38264` | 通過 | 修正後 live JSON `count=4`；四筆車號各異，空補充值保留 `其它問題` |

## UI 證據

不適用：無 UI 變更。錄製 DOM 與 HAR 僅做離線驗證，未複製進 repo。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 錄製回應有兩張同名紀事表，只有一張含「更換數量」 | 中 | 以完整表頭集合唯一辨識，已測試 |
| MMIS 表頭「故障類型說明」與需求用語不同 | 低 | 映射為輸出「故障類別說明」，已測試 |
| C1 表格使用「故障類別說明」，且車組/車號在每筆紀事列中 | 中 | 同時支援兩種說明表頭，逐列車號優先；C1 與 C2 live 回歸通過 |
| 「其它故障現象」 textarea 位於目標紀事表格的目前選取列明細中 | 中 | 以目標表 prefix 與標籤/for 關係定位；未選取列先切換，錄製與 live 驗證通過 |
| 相同明細值的列切換只回傳 currentrow 更新，沒有 textarea 元素 | 中 | 確認選列成功後沿用目前已渲染值；115-C2-38264 四列 live 驗證通過 |
| 第三筆紀事的三種「其它」補充在選列回應中可能只重送 textarea、不重送標籤 | 中 | 先由完整頁面解析三個 label/for 控制項，再依控制項 ID 套用逐列部分更新；115-C2-41266 live 3 筆驗證通過 |

## 安全性與殘留風險

- 沿用現有 `MMISSession`、`MaximoEventClient`；僅查詢、頁籤與分頁 click 事件，無寫入 MMIS 操作。
- 輸入在登入前驗證；唯一且完全相符工單才開啟；分頁不一致時失敗，不回傳部分資料。
- 真實空清單與多頁案例尚未取得錄製，空清單以錄製結構合成測試；多頁邏輯只經程式審查，待有實例時補 live 驗證。負責人：後續執行該工具的維護者。
- `115-C2-38264` 的四筆即時「更換數量」分別為 `8.00`、`4.00`、`16.00`、`4.00`；保留 MMIS 各列原值。
- `mmis-dev-knowledge` 的 `commonErrors/maximo-page-count-must-match-target-table` 已合併本次同名表格辨識經驗，未取代或棄用舊條目。
- `mmis-dev-knowledge` 的 `apiPatterns/maximo-current-row-note-detail-textarea` 已新增逐列補充 textarea 定位規則，未棄用舊條目。

## 後續任務

- 若取得真實空清單或多頁工單，可補錄製並驗證上述分支。
