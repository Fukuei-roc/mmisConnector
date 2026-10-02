# 驗證報告

## 摘要

- 任務：MMIS-024
- 結果：通過
- 驗證者：Codex

## 指令與結果

| 指令 | 結果 |
|---|---|
| `python -m pytest -q` | 全數通過；7 個既有 optional recording 測試略過 |
| `python -m compileall -q src tests tools/mmis_development` | 通過 |
| `git diff --check` | 通過 |
| `python -m pip check` | `No broken requirements found.` |
| `python -m tools.mmis_development.query_work_orders_linked_to_fault_notice 1150910-14` | live HTTP 唯讀查詢成功；3 筆，工作單為 115-C1-35820、115-C2-35988、115-1A-70151 |
| `python -m tools.mmis_development.query_work_orders_linked_to_fault_notice 1150917-41` | 2026-10-02 併單案例修正後 live HTTP 唯讀查詢成功；2 筆，工作單為 115-2A-69254-001、115-C1-36682；兩列通報號均為 1150915-58、狀態為併單 |

## 審查與殘留風險

- 架構：tool 僅作參數、登入及 JSON 輸出；reader 使用正式 HTTP 元件，無瀏覽器依賴。
- 安全：輸入格式與精確結果驗證；憑證沿用環境設定；未寫入錄製內容、cookie 或 token；只發送查詢與頁籤事件。
- 測試：涵蓋錄製 DOM、重複工作單跨頁、空表與缺頁；live 對照三筆指定工單。
- 併單回歸：移除工單列「通報號」必須等於查詢通報號的錯誤假設；新增併單測試，完整 pytest 再次通過，原始三筆案例 live 再次成功。
- UI 證據：無 UI 變更，不適用。
- 殘留風險：依賴 MMIS 可見標籤與分頁 DOM；若網站改版，查詢會報錯，需要更新 parser。
- 共用知識庫：`commonErrors/maximo-page-count-must-match-target-table` 已新增，未取代既有條目。
- 後續任務：無必要後續任務。
