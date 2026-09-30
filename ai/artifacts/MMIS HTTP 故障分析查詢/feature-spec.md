# 功能規格書

## Metadata

- 功能：MMIS HTTP 故分析查詢
- 負責人：專案使用者／Codex
- 狀態：已實作並完成唯讀 live 驗證（2026-09-30）
- 風險等級：高（MMIS 身分驗證與內部網路讀取；遠端唯讀）

## 問題

使用者目前需手動進入「故障通報管理」、依通報號過濾、開啟明細並切到「故障分析」，才能取得五個所需欄位；專案尚無 HTTP-only 命令自動完成此流程。

## 使用者與目標

- 使用者：具有 MMIS 故障通報查詢權限的內部使用者。
- 輸入一個通報號，以純 HTTP/session 流程取得「事故現象」、「處理概況」、「故障原因」、「處理情形」、「改善對策」。
- stdout 只列印 UTF-8 JSON，不產生檔案。

## 非目標

- 不寫入或儲存上述三個可編輯欄位。
- 不新增瀏覽器、Playwright 或 fallback。
- 不批次查詢，不產生 JSON/Excel/log 檔。
- 不改變既有命令與 production CLI 契約。

## 使用者故事

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 查詢故障分析 | 身為 MMIS 使用者，我想以通報號查詢五個故障分析欄位，以便供後續程式使用 | 純 HTTP；精確命中一筆；五欄完整且空白保留；stdout 為 JSON；無檔案副作用 |

## 功能需求

- WHEN 通報號不符合 `NNNNNNN-NN`，THE SYSTEM SHALL 在網路呼叫前拒絕。
- WHEN 參數合法，THE SYSTEM SHALL 沿用 `MMISSession` 與 `MaximoEventClient` 進入 `ZZ_FNM`。
- WHEN 清單載入，THE SYSTEM SHALL 由表頭動態解析「通報號」欄位，送出 `setvalue + filterrows`。
- WHEN 結果不是唯一一筆或業務鍵不相符，THE SYSTEM SHALL fail closed。
- WHEN 進入明細，THE SYSTEM SHALL 以標題動態找到「故障分析」頁籤。
- WHEN 分析頁載入，THE SYSTEM SHALL 以 label/for 關聯取得五個 textarea，不依賴動態 ID 或是否可編輯。
- WHEN 欄位為空，THE SYSTEM SHALL 輸出空字串。
- WHEN 任一欄位缺失或重複，THE SYSTEM SHALL 以非零 exit code 輸出去敏 JSON 錯誤。

## 資料與 API

- 命令：`python -m tools.mmis_development.query_fault_notice_analysis <通報號>`
- 輸入：一個通報號，例 `1150828-12`。
- 成功輸出：`success`、`query_name`、`fault_notice`、`analysis`；`analysis` 含指定五欄且順序穩定。
- 錯誤：參數錯誤、找不到、非唯一、業務鍵不符、DOM 漂移或 session/network 錯誤皆不輸出部分成功資料。

## 安全性與隱私

- 沿用 `.env` 認證、同源 HTTPS、CSRF/page state 與禁止 Maximo POST 自動重試的現有控制。
- 不輸出帳密、cookie、token、session ID、動態 target ID 或原始回應。
- 錄製檔僅本機唯讀驗證，不複製入 repository。

## 驗收與驗證計畫

- 單元／整合：格式驗證、動態欄位、event 順序、零筆／多筆／不相符、頁籤與五欄、空白與多行文字、tool JSON 契約。
- 錄製證據：本機 DOM 可完整解析範例五欄。
- 回歸：完整 pytest、compileall、pip check、diff check、安全與依賴邊界掃描。
- E2E：所有離線檢查通過後，可執行一次指定範例的唯讀 live 查詢。
- UI：不適用；本專案無 UI 變更。

## 情境包

- 相關檔案：`fault_notices/query.py`、新 reader、`events.py`、`parser.py`、development tool 與 tests。
- 既有模式：domain Reader + 薄 wrapper；動態 table schema；業務鍵完全相符；JSON stdout。
- 錄製證據：`C:\Docker\maximoFlowRecorder\recordings\2026-09-30_query-fault-notice-analysis`；已核對 changeapp、filter、detail click、analysis tab click 與最終 DOM。
- 假設：命令一次只查一個通報號；輸出 envelope 依既有 tool 慣例保留查詢 metadata。
- 未知：live 環境權限拒絕或 Maximo DOM 未來漂移；均 fail closed。
- 允許變更：新 reader/tool/tests，必要 parser/public API/README/architecture/governance artifacts。
- 不得觸碰：`.env`、外部 recording、不相關使用者修改、瀏覽器自動化與遠端寫入。
- 情境預算：已讀 project/architecture/search map、DoR/DoD、相關 skills、既有 query/reader/parser/tool/tests、recording README/summary/關鍵 HAR events/最終 DOM；跳過靜態資源、完整敏感 headers/cookies 與不相關 domain。
