# 功能規格書

## Metadata

- 功能：以工作單號查詢日檢工單並勾稽故障通報
- 英文名稱：Query Daily Inspection Work Order by Work Order Number and Link Fault Notice
- 負責人：人工產品負責人／Codex
- 狀態：已實作並完成人工驗收（2026-09-24）
- 風險等級：高

## 問題

使用者目前必須在 MMIS「動力車日檢(1A)」中手動切換所有記錄、依工作單號查詢並進入唯一工單，再輸入故障通報號、執行勾稽、確認結果並返回清單。既有 CLI 只能讀取工單已關聯的故障通報，不能執行勾稽寫入操作。

## 使用者

具有 MMIS「動力車日檢(1A)」查詢與故障通報勾稽權限、需要從 Windows 命令列處理單筆資料的內部使用者。

## 目標

- 提供一個 HTTP-only CLI，由使用者輸入工作單號與故障通報號。
- 僅在工作單唯一且完全相符時進入工單。
- 以錄製證實的同一 POST 事件批次執行故障通報號設定與勾稽按鈕點擊。
- 以「故障通報管理」出現完全相符的故障通報號確認成功。
- 成功後返回「清單」頁面，讓同一流程處於可開始下一筆操作的狀態，然後結束程式。
- 對可能已送達 MMIS、但未取得回應的結果不明情況安全失敗，且不自動重送寫入 POST。

## 非目標

- 不修改或取代既有唯讀命令 `query-daily-inspection-work-order-by-number`。
- 不支援一個命令勾稽多筆工作單或多筆故障通報。
- 不自動解除勾稽、刪除或修改既有故障通報。
- 不在返回清單後繼續處理下一筆；批次功能留待後續需求。
- 不新增 Playwright、Selenium、Chrome 或其他瀏覽器 fallback。
- 不把 HAR、cookie、CSRF token、session ID 或完整 MMIS 回應寫入 repo 或 stdout。
- 不在一般自動化測試套件中對 live MMIS 執行勾稽；本次實作完成後可依下列限定授權執行一次 live 驗證。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 以工作單號勾稽故障通報 | 身為有權限的內部使用者，我想輸入工作單號與故障通報號，以便在唯一相符的 1A 工單完成勾稽 | 只對唯一且完全相符的工單執行；確認故障通報出現在管理表格；返回清單；輸出可解析 JSON |

## 使用者旅程

```text
身為具有 MMIS 勾稽權限的內部使用者
我想要執行一個帶有工作單號與故障通報號的 CLI
以便完成單筆勾稽、確認寫入結果並回到清單準備下一次操作
```

範例：

```powershell
python -m mmis_connector `
  query-daily-inspection-work-order-by-number-and-link-fault-notice `
  115-1A-71002 1150923-36
```

## 功能需求

- WHEN CLI 參數不是兩個，THE SYSTEM SHALL 在登入 MMIS 前拒絕執行並顯示用法。
- WHEN 驗證輸入，THE SYSTEM SHALL trim 兩個值，重用既有工作單號驗證，並要求故障通報號非空、最長 20 字元且只含英文字母、數字與連字號。
- WHEN 載入應用程式，THE SYSTEM SHALL 重用既有 HTTP/session 流程進入 `ZZ_PMWO1A`「動力車日檢(1A)」並切換「所有記錄」。
- WHEN 查詢工作單，THE SYSTEM SHALL 只在總筆數恰好一筆、資料列恰好一筆，且「工作單」值與正規化輸入完全相符時繼續。
- WHEN 工單為零筆、多筆、分頁狀態不一致或值不相符，THE SYSTEM SHALL 在勾稽前停止，不得自行選擇第一筆。
- WHEN 進入工單明細，THE SYSTEM SHALL 依標籤文字、`for`／`aria-labelledby` 關係與按鈕文字動態找出「故障通報號」輸入框、「勾稽指定故障通報號」按鈕及標題為「清單」的 tab，不得寫死錄製中的動態 ID。
- WHEN 使用者提供有效輸入且工單唯一完全相符，THE SYSTEM SHALL 直接執行勾稽，不在客戶端預先判斷該故障通報是否已存在；重複勾稽由 MMIS 既有防呆機制處理。
- WHEN 需要執行勾稽，THE SYSTEM SHALL 依錄製流程在同一個 Maximo event POST 內依序送出 `setvalue` 與 `click` 事件。
- WHEN 送出勾稽 POST，THE SYSTEM SHALL 禁止 transport 自動重試，避免因回應遺失而重複寫入。
- WHEN 勾稽回應到達，THE SYSTEM SHALL 重新解析 `summary="故障通報管理"` 的表格，並只在其中出現與輸入完全相符的故障通報號時確認成功。
- WHEN 寫入請求可能已送達但沒有可驗證回應，THE SYSTEM SHALL 以「結果不明、需人工確認」的安全訊息失敗，不得自動重送。
- WHEN 勾稽已確認，THE SYSTEM SHALL 點擊動態解析到的「清單」tab，並以日檢工單清單必要表頭確認已返回清單。
- WHEN 勾稽已確認但無法確認返回清單，THE SYSTEM SHALL 明確回報「勾稽已確認，但返回清單失敗」，不得把它誤報為尚未勾稽。
- WHEN 全部步驟完成，THE SYSTEM SHALL 輸出 UTF-8 JSON 至 stdout，且不得輸出憑證、cookie、CSRF token、session ID、動態 element ID 或完整 response body。
- WHEN 發生任何失敗，THE SYSTEM SHALL 使用非零 exit code；不含敏感資訊的診斷可寫入錯誤 JSON。

## 畫面

不新增或修改本專案 UI。本功能只透過 HTTP 重播既有 MMIS 畫面事件，因此不適用 UI mockup 關卡。

## 資料與 API

- CLI：`query-daily-inspection-work-order-by-number-and-link-fault-notice <工作單號> <故障通報號>`。
- 輸入：工作單號字串、故障通報號字串。
- 正規化：兩者皆 trim；工作單號沿用既有規則；故障通報號長度為 1–20，字元集合為 `[A-Za-z0-9-]`，且首字元必須為英數字。
- 寫入事件：同一個 `POST /maximo/ui/maximo.jsp` 中，先 `setvalue` 至動態解析的故障通報輸入框，再 `click` 動態解析的勾稽按鈕。
- 成功輸出契約：

```json
{
  "success": true,
  "operation_name": "以工作單號查詢日檢工單並勾稽故障通報",
  "work_order": "115-1A-71002",
  "fault_notice": "1150923-36",
  "linked": true,
  "returned_to_list": true
}
```

- 程式不提供 `already_linked` 欄位，也不在送出事件前檢查重複關聯；MMIS 防呆後的回應仍須通過故障通報表格驗證。
- 錯誤：參數無效、找不到工單、工單不唯一或不相符、缺少必要控制項、缺少故障通報管理表格、勾稽後未出現指定通報、結果不明、返回清單失敗。
- 資料模型：不新增本機資料庫或檔案；變更只發生在 MMIS 遠端系統。
- 遷移：無。
- 回滾：程式不提供解除勾稽；錯誤勾稽需由具權限人員依 MMIS 既有人工流程處理。

## 安全性與隱私

- 身分驗證：沿用 `.env` 與 `MMISSession`，帳密不得進入命令列參數、log 或測試 fixture。
- 權限：由 MMIS 帳號權限強制執行；程式不得繞過 MMIS 授權判斷。
- 敏感資料：不得提交原始 HAR；測試 fixture 僅保留完成解析所需的去識別 DOM／event 結構。
- 網路邊界：沿用同源 HTTPS 限制、TLS 驗證與目前 session 的 CSRF/page state。
- 完整性：唯一工單精確比對、勾稽後表格驗證及返回清單驗證均採 fail closed；重複關聯判斷由 MMIS 負責。
- 重試：GET 可沿用既有策略；登入與 Maximo POST（尤其寫入事件）不得自動重試。
- 濫用情境：錯誤的工作單號或故障通報號可能建立錯誤關聯，因此任何模糊命中、解析異常或結果不明都必須停止。

## 驗收標準

- 新命令只接受兩個參數，並在任何網路呼叫前拒絕無效輸入。
- 使用錄製案例 `115-1A-71002` 與 `1150923-36` 的去敏 fixture，可驗證正確的事件順序、動態 target 解析、勾稽確認與返回清單確認。
- 工單零筆、多筆、不完全相符或分頁不一致時，不會送出勾稽事件。
- 即使「故障通報管理」原先已有相同故障通報，程式仍送出勾稽事件，並由 MMIS 既有防呆機制處理。
- 寫入事件是單一 POST 內的 `setvalue` 後接 `click`，且 transport 不自動重試。
- 回應沒有指定故障通報號時不得回報成功。
- 完成後一定驗證返回日檢工單清單，成功 JSON 的 `returned_to_list` 為 `true`。
- 寫入結果不明與「已勾稽但返回清單失敗」可由錯誤訊息明確區分。
- 既有三個 CLI 與公開 Python API 測試維持通過。
- repo 不新增瀏覽器依賴、敏感常值、原始 HAR 或 session evidence。
- 離線測試全部通過後，以工作單號 `115-1A-71002` 與故障通報號 `1150923-36` 執行一次 live MMIS 驗證，並記錄去敏後的指令結果、勾稽確認與返回清單證據。

## 驗證計畫

- 單元測試：輸入驗證、動態控制項解析、唯一命中保護、批次事件 payload、MMIS 重複防呆回應後的結果驗證、成功確認、結果不明、返回清單驗證。
- 整合測試：使用去敏錄製 DOM／event fixture 與 fake session 跑完整 HTTP-only 流程，不連線 MMIS。
- CLI 測試：參數數量、handler dispatch、成功 JSON、失敗 exit code。
- 回歸：`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`、`git diff --check`。
- 安全性：掃描瀏覽器依賴、明文敏感資訊、HAR／cookie／token／session ID；確認 POST 不自動重試。
- E2E：本次已取得一次性人工授權。僅在離線測試、完整回歸與安全性檢查通過後，使用工作單號 `115-1A-71002` 與故障通報號 `1150923-36` 執行一次 live MMIS 勾稽；不得換用其他資料、批次執行或自動重跑。
- 視覺：不適用，無 UI 變更。
- 手動：核對成功 JSON、MMIS 故障通報管理內容與返回清單狀態。使用者已說明測試造成的 MMIS 資料變更可由使用者手動回復；驗證報告須明確列出實際變更與回復責任。

## 情境包

- 相關檔案：`src/mmis_connector/query_fault_notices_linked_to_daily_inspection_work_order_by_number.py`、`src/mmis_connector/events.py`、`src/mmis_connector/cli.py`、`src/mmis_connector/parser.py`、對應 tests 與 `README.md`。
- 既有模式：HTTP-only session、`open_all_records()`、動態表格 prefix／欄位解析、唯一命中、XML／CDATA flatten、stdout JSON。
- 錄製證據：`C:\Docker\maximoFlowRecorder\recordings\2026-09-24_query-daily-inspection-work-order-by-number-and-cross-check-fault-reports`；只讀取本機證據，不複製原始 HAR。
- 允許變更：上述相關 `src`／`tests`、README、此 Epic 的 artifacts 與 kanban metadata；實際範圍仍須由核准後的任務卡限定。
- 不得觸碰：`.env`、錄製原始檔、其他 MMIS 功能行為、瀏覽器自動化，以及一次性授權測試資料以外的外部系統資料。
- Live 寫入授權：本次實作驗證可對 `115-1A-71002` 與 `1150923-36` 執行一次勾稽；不得延伸為其他工作單、其他故障通報、批次操作或失敗後自動重跑。資料回復由使用者手動處理。
- 未知事項：live MMIS 的權限拒絕與重複勾稽錯誤回應尚無錄製案例；以 fail closed 與不重試處理。
- 情境預算：讀取專案地圖、架構地圖、搜尋指南、既有 reader／CLI／event transport、相關測試、錄製摘要與關鍵事件／DOM 片段；跳過不相關功能及原始 HAR 大量靜態資源。
