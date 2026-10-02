# 驗證報告

## 摘要

- 任務：MMIS-027 故障通報整合唯讀查詢
- 結果：通過，待人工驗收
- 驗證者：Codex，2026-10-02

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_fault_notice_full_detail.py tests/test_linked_work_orders.py tests/test_repair_work_orders.py tests/test_read_fault_notice_atp_analysis.py -q` | 通過 | 整合、獨立 reader 與 ATP 解析；錄製 DOM 測試依本機錄製資料可用性跳過 |
| `python -m pytest` | 通過 | 168 passed、9 skipped，1.66s；跳過的是環境缺少錄製資料的既有條件式測試 |
| `python -m compileall -q src tools` | 通過 | 無輸出 |
| `git diff --check` | 通過 | 無空白錯誤；Git 顯示 Windows 行尾轉換提示 |
| `python -m tools.mmis_development.query_fault_notice_full_detail bad-notice` | 預期失敗 | 退出碼 1；stdout 為 `MMISClientError` JSON，登入前拒絕格式錯誤 |
| `python -m tools.mmis_development.query_fault_notice_full_detail 1150210-36` | 通過 | 唯讀 live 查詢；ATP=true，段修 4 筆、CA 0 筆，五欄及 ATP 三欄均存在 |
| `python -m tools.mmis_development.query_fault_notice_full_detail 1150930-09` | 通過 | 唯讀 live 查詢；ATP=false，段修 2 筆、CA 1 筆，ATP 分析為 null |
| PowerShell：以 `ConvertFrom-Json`、`ConvertTo-Json -Compress` 比對 `1150930-09` 的整合結果與三個既有獨立命令 | 通過 | `linked=true`、`repair=true`、`analysis=true` |
| PowerShell：比對 `1150210-36` 的整合 ATP 分析與既有 ATP 命令 | 通過 | `atp=true` |

## 變更檔案

- 新增：`src/mmis_connector/fault_notices/full_detail.py`、`tools/mmis_development/query_fault_notice_full_detail.py`、`tests/test_fault_notice_full_detail.py`。
- 修改：`src/mmis_connector/fault_notices/{linked_work_orders,repair_work_orders}.py`、`tests/test_architecture.py`、架構／搜尋／專案地圖與本 Epic 產出物。
- 使用者既有的 `Prompt.md` 未動。

## UI 證據

無 UI 變更；螢幕截圖不適用。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 架構測試固定列出 production module 和 development tool 數量，新檔加入後測試失敗 | 中 | 已將新 reader 分類並更新工具數量；全套測試通過 |
| 兩張工單表欄位不同，跨表合併會遺失或混淆欄位 | 中 | 已依人工確認分成 `段修工單`、`CA查修工單` 兩個頂層陣列 |

## 安全性與可維護性審查

- 功能：唯一通報驗證、兩表獨立分頁與去重、條件式 ATP 分析，離線及兩筆 live 路徑通過。
- 認證與權限：重用既有 `.env`、`MMISSession` 與 `MaximoEventClient`，無新授權或寫入事件。
- 輸入／網路：格式於登入前驗證；所有請求沿用既有同源 HTTPS、CSRF 與 page state。
- 密鑰與隱私：不記錄帳密、cookie、token 或原始 HTML；業務資料只輸出至 stdout，不落盤。
- 架構：production reader 不 import development tool；現有四個獨立工具的輸出契約保持原樣。
- 核准建議：可交由使用者人工驗收。

## 殘留風險

- 本次兩筆 live 通報未覆蓋兩張表同時跨頁；已以離線整合測試驗證兩表各自跨頁及事件序號接續，尚無此情境的 live 證據。
- MMIS DOM 若變更語意頁籤、欄位或表格標題，解析器會以 JSON 錯誤停止，需依新錄製資料調整。
- 錄製 DOM 測試在本環境有 9 項條件式跳過；全套其餘測試通過。

## 後續任務

- 使用者驗收單一 JSON 的欄位與命名；若需其他輸出格式，再立新任務。
