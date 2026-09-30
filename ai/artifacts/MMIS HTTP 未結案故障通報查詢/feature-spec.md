# 功能規格書

## Metadata

- 功能：MMIS HTTP 未結案故障通報查詢
- 英文名稱：Query Unclosed Fault Notices
- 負責人：專案使用者／Codex
- 狀態：已實作並完成唯讀 live 驗證（2026-09-30）
- 風險等級：高（MMIS 身分驗證與內部網路讀取）

## 問題

使用者目前需在 MMIS「故障通報管理」中手動套用「故障通報未結案清單」、輸入固定篩選條件並翻頁，才能取得本段 A、B 級未結案故障通報。既有 repository 尚無一個零參數、HTTP-only、只將完整資料列輸出為 stdout JSON 的命令。

## 使用者

具有 MMIS 故障通報查詢權限、需要從 Windows 命令列取得未結案故障通報的內部使用者。

## 目標

- 提供零自訂參數的 development tool 命令。
- 不啟動或依賴瀏覽器，只重用既有 `MMISSession`、`MaximoEventClient` 與 parser。
- 固定套用「故障通報未結案清單」。
- 固定以 `配屬段別名稱=新竹機務段` 與 `事故等級=A,B` 篩選。
- 擷取所有分頁並將完整資料以 UTF-8 JSON 印到 stdout。
- 不建立 JSON、Excel、log 或其他輸出檔案。

## 非目標

- 不接受 depot、事故等級、日期、狀態或其他自訂查詢參數。
- 不下載或格式化 Excel。
- 不新增正式 production CLI subcommand；本次入口位於 `tools/mmis_development/`。
- 不新增 Playwright、Selenium、Chrome 或其他瀏覽器 fallback。
- 不複製或提交 HAR、DOM、cookie、CSRF token、session ID 或完整 MMIS 回應。
- 不修改 MMIS 遠端資料。
- 不改變既有「本段未處理通報」與日檢工單相關命令的行為或輸出契約。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 查詢未結案故障通報 | 身為有權限的內部使用者，我想執行一個不帶參數的命令，以便取得新竹機務段 A、B 級未結案故障通報 | 全流程只用 HTTP；stdout 為有效 JSON；資料列完整涵蓋所有分頁；不產生檔案 |

## 使用者旅程

```text
設定 .env
→ 執行 python -m tools.mmis_development.query_unclosed_fault_notices
→ HTTP 登入並重用同一 Session
→ 進入故障通報管理（ZZ_FNM）
→ 套用「故障通報未結案清單」
→ 設定配屬段別名稱=新竹機務段
→ 設定事故等級=A,B 並送出 filterrows
→ 依序取得所有分頁並驗證一致性
→ stdout 印出 JSON
```

## 功能需求

- WHEN 命令帶有任何位置參數，THE SYSTEM SHALL 在載入設定或發出網路請求前拒絕執行並輸出安全的 JSON 錯誤。
- WHEN 命令合法啟動，THE SYSTEM SHALL 從既有環境設定載入 MMIS 憑證，以同一個 `requests.Session` 登入並維持 page state。
- WHEN 進入故障通報管理，THE SYSTEM SHALL 重用既有 `changeapp` 流程載入 `ZZ_FNM`，不得重造登入或 transport。
- WHEN 開啟儲存查詢選單，THE SYSTEM SHALL 套用「故障通報未結案清單」並驗證回應確認該查詢名稱。
- WHEN 解析查詢表格，THE SYSTEM SHALL 以必要表頭集合辨識唯一的動態 table prefix，不得寫死錄製中的 `m6a7dfd2f`。
- WHEN 設定固定條件，THE SYSTEM SHALL 由解析出的表頭 mapping 找出「配屬段別名稱」與「事故等級」欄位，先送出配屬段別 `setvalue`，再於同一個後續 POST 依序送出事故等級 `setvalue` 與 `filterrows`。
- WHEN 最終篩選回應返回，THE SYSTEM SHALL 將其視為不重複包含 toolbar 查詢名稱的局部表格片段，並驗證表格結構、分頁範圍與資料列筆數；saved query 名稱已在前一步選取回應驗證。
- WHEN 總筆數超過單頁筆數，THE SYSTEM SHALL 由同一 table prefix 解析啟用的下一頁控制項，逐頁擷取直到資料列數等於初始總筆數。
- WHEN 分頁範圍不連續、總筆數改變、下一頁控制項缺失、表頭不唯一或最終筆數不符，THE SYSTEM SHALL fail closed，不得輸出部分成功資料。
- WHEN 結果為零筆，THE SYSTEM SHALL 回傳成功且 `count=0`、`records=[]`。
- WHEN 結果包含空欄位或 ATP checkbox，THE SYSTEM SHALL 分別輸出空字串與 boolean。
- WHEN 成功，THE SYSTEM SHALL 只將 UTF-8 JSON 印到 stdout；不得建立任何檔案。
- WHEN 發生錯誤，THE SYSTEM SHALL 以非零 exit code 輸出不含憑證、cookie、token、session ID、動態 element ID 或完整 response body 的 JSON 錯誤。

## 畫面

不新增或修改本專案 UI；不適用 UI mockup 關卡。錄製截圖只作為本機分析證據，不納入 runtime 或 repository。

## 資料與 API

- 命令：`python -m tools.mmis_development.query_unclosed_fault_notices`
- 使用者參數：無；任何額外參數均視為錯誤。
- 環境設定：沿用 `MMISConfig.from_env()` 所需的既有 `.env` 設定；環境設定不屬於本命令的自訂查詢參數。
- 固定儲存查詢：`故障通報未結案清單`。
- 固定篩選：`配屬段別名稱=新竹機務段`、`事故等級=A,B`。
- 輸出欄位：沿用故障通報 parser，包含車次、車組/車號、發生日期、發生時間、事故等級、故障地點、ATP故障、故障現象、立案人員、通報人員、通報單位、通報股室、狀態、通報號、配屬段別、配屬段別名稱、顏色查詢。
- 成功輸出契約：

```json
{
  "success": true,
  "query_name": "故障通報未結案清單",
  "filters": {
    "配屬段別名稱": "新竹機務段",
    "事故等級": "A,B"
  },
  "count": 31,
  "records": []
}
```

- `count` 必須等於 `records` 陣列長度；上例的 31 來自 2026-09-30 錄製案例，不是程式中的固定預期值。
- 資料模型：不新增本機資料庫或輸出檔案。
- 遷移與回滾：無；本功能唯讀，回滾為移除新增 component、tool 與對應測試。

## 安全性與隱私

- 身分驗證：沿用 `.env` 與 `MMISSession`；不得將帳密放入命令列、原始碼、測試 fixture 或輸出。
- 權限：由 MMIS 帳號權限強制執行；程式不得繞過授權。
- 網路邊界：沿用既有同源 HTTPS、TLS 驗證、timeout、CSRF、PAGESEQNUM、UISESSIONID 與 xhr sequence 管理。
- 重試：沿用既有 transport 規則；Maximo event POST 不得自動重試。
- 敏感資料：原始 recording 僅能在本機只讀分析，不得複製到 repo；stdout 不輸出 page URL、session state 或 download URL。
- 完整性：HTTP 200 不代表成功；必須驗證已選查詢、表格 schema、分頁連續性、固定 total 與最終筆數。

## 驗收標準

- 新命令不接受自訂參數，且額外參數會在任何網路呼叫前被拒絕。
- 程式不安裝、不匯入、不啟動瀏覽器工具，也沒有瀏覽器 fallback。
- 錄製事件順序為：開啟查詢選單、選擇「故障通報未結案清單」、設定配屬段別名稱、設定事故等級並觸發 `filterrows`。
- 動態 table prefix 與欄位編號由回應表頭解析；測試不得依賴錄製中的固定 prefix。
- 2026-09-30 去敏錄製結構可辨識 `1–20/31`，並由模擬的下一頁回應合併成 31 筆。
- 零筆、單頁、多頁、表頭缺失、分頁不連續、total 改變與 next control 缺失均有離線測試。
- 成功 stdout 是單一有效 JSON 文件，包含 `success`、`query_name`、固定 `filters`、`count`、`records`；不建立檔案。
- 既有 development tools、public API 與完整測試套件維持通過。
- repository 不新增 HAR、session evidence、cookie、token、帳密、完整內部資料或瀏覽器依賴。

## 驗證計畫

- 單元測試：查詢常數、動態欄位 mapping、event payload 與 xhr sequence、零筆／單頁／多頁、分頁錯誤、工具零參數契約、錯誤 redaction。
- 整合測試：以 fake session 與最小去敏 HTML/XML fixture 跑完整 HTTP-only 查詢，不連線 MMIS、不產生檔案。
- 錄製證據測試：本機 recording 存在時，唯讀驗證最終 DOM 可解析 20 筆、總數 31、必要表頭與下一頁 target；不存在時標記 optional skip，不將 recording 複製進 repo。
- 回歸：`python -m pytest -rs`、`python -m compileall -q src tests tools/mmis_development`、`python -m pip check`、`git diff --check`。
- 安全性：掃描瀏覽器依賴、敏感常值、HAR／session evidence、檔案寫入與 stdout 契約；確認 production 不反向 import development tool。
- E2E：規格與高風險任務卡經人工核准、離線驗證全通過後，才對 live MMIS 執行一次唯讀命令；不得把回應內容或 session state 寫入檔案。
- 視覺：不適用，無 UI 變更。

## 情境包（Context Pack）

- 任務：新增 HTTP-only「查詢未結案故障通報」零參數 development tool。
- 相關檔案：`tools/mmis_development/_support.py`、`query_unprocessed_fault_notices.py`、`src/mmis_connector/fault_notices/query.py`、`events.py`、`parser.py`、對應 tests 與 `tools/mmis_development/README.md`。
- 既有模式：薄 wrapper；正式 Query 放在 domain package；單一 `MMISSession`；`MaximoEventClient.post_events()`；動態 table schema；分頁連續性與 total 一致性檢查；stdout JSON／stderr 診斷。
- 錄製證據：`C:\Docker\maximoFlowRecorder\recordings\2026-09-30_query-unclosed-fault-notices`；關鍵事件為 changeapp、saved-query click、depot setvalue、level setvalue + filterrows；最終畫面為 `1 - 20/31`。
- 參考 skill：`mmis-query-open-b-level-fault-notices` 已驗證相同 HTTP 事件型態，但其下載檔案、可選參數、session cache、log 檔與 Playwright fallback 均不納入本次實作。
- 假設：使用者所稱「需要的資料」是錄製畫面該表格的所有欄位與全部分頁；固定條件以錄製 mark 為準。
- 未知事項：live MMIS 的零筆回應與 session 權限拒絕畫面沒有本次 recording；以既有 parser／auth 的 fail-closed 行為及離線測試處理。
- 允許變更的檔案：新增 fault-notice Query component／development tool／tests，以及必要的 parser export、development README、context map、本 Epic artifacts 與 kanban metadata；實際範圍由核准後任務卡限定。
- 不得觸碰：`.env`、外部 recording、既有命令契約、其他 domain 行為、瀏覽器自動化、不相關的 `mmis-post-feature-refactoring-guide.md` 使用者修改。
- 驗證指令：針對性 pytest、完整 pytest、compileall、pip check、diff check、敏感資訊與瀏覽器依賴掃描；經核准後一次唯讀 live 查詢。
- 風險等級：高；涉及認證與內部網路，但僅讀取、不執行遠端 mutation。
- 情境預算備註：已讀專案／架構／搜尋地圖、共用流程與 DoR、既有 fault-notice query／event／parser／tool／tests、MMIS 知識庫相關 confirmed 條目、錄製 README／摘要／關鍵 HAR events／DOM／截圖及對應 skill；跳過 HAR 中靜態資源、完整敏感 header/cookie/body 與不相關 domain。
