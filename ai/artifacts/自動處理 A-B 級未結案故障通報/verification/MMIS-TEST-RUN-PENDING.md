# 驗證報告

## 摘要

- 任務：將核簽中試車報告工單納入待簽核 JSON。
- 結果：通過指定案例與離線測試，待人工驗收。
- 驗證者：Codex。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m tools.mmis_development.query_fault_notice_full_detail 1151027-16` | 成功 | 讀到 `115-C2-46115` 為 C2 且完工待回報；頂層待簽核檢查值為 false。 |
| `python -m tools.mmis_development.query_temporary_repair_work_order_detail 115-C2-46115` | 成功 | 試車報告 `115-C2-46115-001` 為核簽中。 |
| `python -m pytest -q` | exit code 0 | 包含同步寫入案例、C1 空結果、非目標母單與錯誤子單；錄製 HAR 相關既有測試照原設定跳過。 |
| `python -m compileall -q tools/mmis_development/auto_process_unclosed_ab_fault_notices.py tests/test_auto_process_unclosed_ab_fault_notices.py` | exit code 0 | 語法編譯通過。 |
| `git diff --check` | exit code 0 | 無空白格式錯誤。 |
| 指定列更新後直接查詢 SQLite | 成功 | `1151027-16` 的 `待簽核工單` 為 `["115-C2-46115-001"]`。 |

## UI 證據

- 無 UI，無螢幕截圖。

## 審查發現

- 架構：重用既有唯讀工具及原本 JSON 欄位，不新增 schema 或遠端寫入。
- 安全：只查符合級別與狀態的母單；核對查詢號碼、報告筆數及子單號歸屬；SQL 使用參數。
- 測試：以暫存 SQLite 驗證完整同步結果，並讀回正式指定列。

## 殘留風險

- 本次未執行完整正式同步，因既有指令後續可能觸發 MMIS 遠端分析寫入。其他通報的子單資料將於下次同步重算。
- 後續 MMIS 狀態若變更，下一次同步會依當時資料重算指定欄位。
