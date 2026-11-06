# 驗證報告

## 摘要

- 任務：為 auto-link 正式 CLI 增加每次執行的 JSONL 診斷紀錄。
- 結果：通過本機離線驗證。
- 驗證者：Codex；另由獨立代理審查安全性、正確性與維護性。兩項審查發現已修正並複審。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest -o addopts= tests/test_auto_link_logging.py tests/test_cli.py -q` | 13 passed | 覆蓋零筆、成功勾稽、敏感值排除、CLI 失敗、handler 關閉、工作目錄變動與寫入失敗警告。 |
| `python -m pytest -o addopts= -q` | 608 passed, 48 skipped | 48 個既有選用錄製資料相關測試依原條件跳過。 |
| `python -m compileall -q src tests` | exit 0 | 語法檢查。 |
| `python -m pip check` | `No broken requirements found.` | 依賴檢查。 |
| `git diff --check` | exit 0 | Git 另顯示原工作樹 CRLF 轉換提示。 |
| `git check-ignore -v logs/auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders/2026-11-06/sample.jsonl` | 命中 `/logs/*` | 執行 log 不納入 Git。 |
| `python -c "from mmis_connector.run_logging import PROJECT_ROOT; print(PROJECT_ROOT)"` | `C:\Docker\mmisConnector` | 本機根目錄解析正確。 |

## UI 證據

此任務沒有 UI，螢幕截圖不適用。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 以目前工作目錄建立 log，可能寫到專案外。 | 中 | 改由 source module 定位專案根目錄，離線測試從其他目錄啟動仍寫回專案。 |
| 檔案開啟後寫入失敗，原始 `FileHandler` 沒有安全且明確的警告。 | 中 | 寫入錯誤只在 stderr 發出一次安全化警告；測試確認不洩漏錯誤內容。 |

## 殘留風險

- 這次沒有重跑會寫入 MMIS 的正式批次；實際 MMIS 勾稽流程沿用既有程式，離線測試直接檢查產生的 JSONL。
- 若 log 檔案開啟後寫入失敗，批次依原有遠端寫入判定繼續，stderr 會警告，但 log 可能不完整。
- 若將套件安裝成獨立 wheel，module 路徑可能不再指向此專案；該部署方式需要另定 log 根目錄。
- 零筆查詢事件只能證明程式當時收到零筆，無法證明 MMIS 中工單當時的歷史狀態。
