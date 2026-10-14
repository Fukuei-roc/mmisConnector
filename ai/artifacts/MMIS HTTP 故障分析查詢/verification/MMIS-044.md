# 驗證報告：MMIS-044

## 摘要

- 任務：完整故障通報新增故障分析素材
- 結果：通過（2026-10-14）
- 驗證者：Codex

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_fault_notice_analysis_materials.py tests/test_fault_notice_full_detail.py -q` | 通過 | 分類、欄位、重試、錯誤隔離、CLI JSON 與原 Reader 回歸 |
| `python -m pytest -o addopts='' -q` | 227 passed, 32 skipped | skipped 均為本機缺少錄製 DOM/HAR 的既有條件測試 |
| `python -m compileall -q src/mmis_connector/fault_notices tools/mmis_development/query_fault_notice_full_detail.py tests/test_fault_notice_analysis_materials.py` | 通過 | 無語法錯誤 |
| `python -m pip check` | 通過 | No broken requirements found |
| `git diff --check` | 通過 | 僅有 Windows LF/CRLF 提示，無 whitespace error |
| `python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14` | 通過兩次 | stdout 均為合法 JSON；第二次摘要驗證欄位與巢狀筆數 |

## 實際 MMIS 唯讀查詢

- exit code 0；原頂層最後新增 `故障分析素材`；stderr 0 行。
- 臨時檢修工單：`115-C1-35820`、`115-C2-35988` 均成功，各自的維修程序概況 count=1。
- 日檢工單：`115-1A-70151` 成功，檢修記錄與重要事項紀錄 count 均為 0。
- 定期檢修工單：空陣列；本通報沒有 2A/3A 工單。
- 成功項目均只含指定欄位；未列印或保存完整通報明細至驗證檔案。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 新增 production module 必須加入固定架構清單與元件庫文件 | 低 | 已更新 `test_architecture.py` 與 production inventory |
| 原 `MMISSession` 的 GET 有底層重試；新邏輯最多執行三次完整工單查詢 | 低 | 已記錄；Maximo POST 仍由既有 Client 禁止 transport 自動重試 |
| 指定通報未含定檢工單 | 低 | 以 mock 測試 2A/3A 派發、巢狀與文字保留；未聲稱定檢 live 驗證 |

## 安全與架構審查

- 原有 `.env` 與 `MMISSession` 認證方式未改；共用同一個 session，沒有新密鑰、檔案輸出或外部 URL。
- 三種詳細查詢仍由既有 Reader 和同源 HTTPS Client 執行；新增流程唯讀且循序。
- 非暫時性錯誤（找不到、格式、登入或權限）不重試；單筆錯誤不阻斷完整通報 JSON。
- 診斷日誌只含工作單號、錯誤類型或 MMIS 安全錯誤文字，不含憑證、cookie 或完整通報。
- UI 證據：不適用，無 UI 變更。

## 殘留風險

- MMIS 其他通報或 2A/3A 明細頁可能有未在此通報 live 測到的 DOM 差異；Reader 遇到解析異常會保留該工單失敗項目。
- 當原始故障通報主查詢本身失敗時，既有 CLI 仍輸出整體錯誤 JSON；此功能只隔離後續工單明細錯誤。
