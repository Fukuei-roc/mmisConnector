# 功能規格書

## Metadata

- 功能：以工作單號查詢日檢工單內容
- 負責人：專案使用者
- 狀態：人工已核准（2026-09-23，使用者指示「好的，請開始實作。」）
- 風險等級：高（重用 MMIS 身分驗證並送出內網 HTTP event）

## 問題

使用者目前必須在 MMIS「動力車日檢(1A)」中手動切換所有記錄、以工作單號過濾、進入命中的工單，再人工抄錄「故障通報管理」表格。現有 HTTP 模組只能依車組／日期取得工單清單，尚不能以工作單號直接進入工單明細，也沒有可供後續程式可靠判斷「有資料」與「空資料」的 JSON 輸出。

## 使用者

需要由 Windows 本機命令列查詢 MMIS 日檢工單內容，並讓後續程式讀取結果的內部使用者。

## 目標

- 提供接受工作單號參數的 CLI 子命令。
- 全程重用既有 `MMISSession`、`MaximoEventClient` 與 Maximo table parser，不依賴瀏覽器。
- 命中唯一工單後，以 HTTP event 進入工單明細並擷取「故障通報管理」表格。
- 將結果以 UTF-8 JSON 印到 stdout，並以穩定欄位明確表示表格是否為空。

## 非目標

- 不啟動或操控 Playwright、Chrome、Selenium 或其他瀏覽器。
- 不修改 MMIS 工單或故障通報資料。
- 不擷取「故障通報管理」以外的工單明細欄位。
- 不下載 Excel，不改動錄製檔案。
- 不建立、修改或儲存任何結果檔案。
- 不重新開發登入、app 切換、event POST 或通用 Maximo table parser。
- 不把 cookie、session id、CSRF token、帳密或完整 MMIS response 寫入 JSON、log、測試 fixture 或 repository。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 以工作單號取得故障通報 | 身為內部使用者，我想在命令列輸入日檢工作單號，以便取得該工單勾稽的故障通報 JSON | 不啟動瀏覽器；命中唯一工單後在 stdout 印出完整且有效的 UTF-8 JSON |
| 判斷故障通報是否為空 | 身為後續程式的開發者，我想以固定欄位判斷故障通報是否存在，以便分流後續處理 | 有資料時 `has_fault_notices=true`；空資料時 `has_fault_notices=false`、`count=0`、`records=[]`，且仍為成功結果 |

## 使用者旅程

```text
身為 MMIS 內部使用者
我執行 python -m mmis_connector query-daily-inspection-work-order-by-number 115-1A-70048
系統登入 MMIS、進入動力車日檢(1A)、切換所有記錄並以工作單 C:5 過濾
系統確認唯一命中且工作單號完全相符，再以 HTTP click event 進入該工單
系統擷取「故障通報管理」表格並把 JSON 印到 stdout
後續程式依 has_fault_notices、count 與 records 判定資料是否為空
```

## 功能需求

- WHEN 使用者提供工作單號，THE SYSTEM SHALL 在任何網路請求前 trim 並驗證其為非空且只含英數字與連字號的安全值。
- WHEN CLI 執行，THE SYSTEM SHALL 使用既有 `MMISSession` 登入並重用同一 HTTP session。
- WHEN 載入日檢工單應用程式，THE SYSTEM SHALL 重用 `MaximoEventClient.load_app()` 切換到 `ZZ_PMWO1A`，不得啟動瀏覽器。
- WHEN 執行查詢，THE SYSTEM SHALL 依錄製證據先選擇「所有記錄」，再對動態解析出的日檢表格 `C:5` 送出工作單號 `setvalue` 與 `filterrows` event。
- WHEN 查詢結果為零筆，THE SYSTEM SHALL 回傳安全錯誤且不得點擊舊結果或任意資料列。
- WHEN 查詢結果超過一筆、找不到唯一表格、或唯一資料列的「工作單」不等於輸入值，THE SYSTEM SHALL fail closed，不得自行挑選第一筆。
- WHEN 查詢唯一命中，THE SYSTEM SHALL 依動態表格 prefix 對該列「工作單」儲存格送出 `click` event 以進入工單內容。
- WHEN 工單內容載入，THE SYSTEM SHALL 只選取 `summary="故障通報管理"` 且表頭完整包含「故障通報號、發生日期、車組/車號、故障現象」的唯一表格。
- WHEN 表格有資料，THE SYSTEM SHALL 依畫面順序輸出所有資料列；儲存格內的 `<br>` SHALL 正規化為 `\n`，不得遺失多行故障現象。
- WHEN 「故障通報管理」表格存在但沒有資料列，THE SYSTEM SHALL 視為成功的業務空結果，輸出 `has_fault_notices: false`、`count: 0`、`records: []`。
- WHEN 表格本身、必要表頭或工單明細識別不存在，THE SYSTEM SHALL 視為解析／流程錯誤，不得誤報為空資料。
- WHEN 結果建立完成，THE SYSTEM SHALL 延續既有 CLI 規則，以 UTF-8、`ensure_ascii=false` 與縮排格式只在 stdout 印出 JSON，不得建立結果檔案。
- WHEN CLI 成功或失敗，THE SYSTEM SHALL 只在 stdout 輸出 JSON；診斷不得包含敏感 session 資訊。

## 畫面

不適用；本功能只有 CLI、HTTP 請求與 stdout JSON，不變更 UI。

## 資料與 API

- CLI：`query-daily-inspection-work-order-by-number <工作單號>`。
- 查詢欄位：日檢工單清單動態 table prefix 下的 `C:5`（錄製案例為工作單 `115-1A-70048`）。
- 明細表格：`summary="故障通報管理"`。
- 記錄欄位：`故障通報號`、`發生日期`、`車組/車號`、`故障現象`，值皆為字串。
- 成功 JSON 契約：

```json
{
  "success": true,
  "query_name": "以工作單號查詢日檢工單內容",
  "work_order": "115-1A-70048",
  "has_fault_notices": true,
  "count": 6,
  "records": [
    {
      "故障通報號": "1150916-17",
      "發生日期": "2026/09/16",
      "車組/車號": "EMU933",
      "故障現象": "EM9334代碼:241故障,牽引MOCK1~4有接觸器未閉合\nED9332端MMI時速表刻度0~10位置有尖銳物割狠"
    }
  ]
}
```

- 空資料 JSON 契約：

```json
{
  "success": true,
  "query_name": "以工作單號查詢日檢工單內容",
  "work_order": "115-1A-70048",
  "has_fault_notices": false,
  "count": 0,
  "records": []
}
```

- stdout 成功結果：印出上述完整 JSON，不包含檔案路徑欄位。
- 錯誤輸出：沿用 CLI 的 `success: false`、安全錯誤型別與訊息，exit code 為 1。
- 資料模型／遷移：無資料庫變更；回滾為移除新 CLI、明細 reader 與對應測試。

## 安全性與隱私

- 身分驗證：沿用 `.env` 與 `MMISSession`，不新增憑證儲存方式。
- 權限：只使用登入帳號原有 MMIS 讀取權限，不繞過授權。
- 網路邊界：所有請求沿用 `MMISSession.request` 的 HTTPS 同源限制、timeout 與安全錯誤封裝。
- 輸入：工作單號只會作為 JSON event value，不拼接為 shell command、URL、HTML 或檔案路徑。
- 敏感資料：錄製 HAR、DOM 與真實 session evidence 只作本機唯讀分析，不複製進 repository。

## 驗收標準

- `python -m mmis_connector query-daily-inspection-work-order-by-number 115-1A-70048` 可由命令列解析工作單參數並執行 HTTP-only 流程。
- 事件順序與錄製證據一致：進入 `ZZ_PMWO1A`、所有記錄、`C:5` 查詢、唯一命中驗證、點擊工作單列、解析明細。
- 對錄製的最終 DOM 離線解析可得到 6 筆記錄，故障通報號依序為 `1150916-17`、`1150916-59`、`1150917-23`、`1150917-51`、`1150918-02`、`1150918-03`。
- 第一、二筆多行故障現象完整保留並以 `\n` 分隔，不包含 HTML `<br>`。
- 明細表格存在但零列時，stdout 為成功 JSON，且 `has_fault_notices=false`、`count=0`、`records=[]`。
- 找不到工作單、查詢多筆、結果不完全相符、明細表格缺失與表頭漂移均回傳 exit code 1。
- 既有 `query-daily-inspection-work-orders` 與 `query-unprocessed-fault-notices` 行為及測試維持通過。
- 原始碼與測試不新增 Playwright／Selenium 依賴，也不包含錄製資料中的敏感值。

## 驗證計畫

- 單元測試：工作單輸入驗證、CLI 參數、事件順序、唯一命中保護、明細 6 筆解析、多行文字、空表、表格缺失，以及 stdout 僅含 JSON。
- 整合測試：使用外部錄製 DOM 做唯讀離線解析，不把敏感 HAR／DOM 複製進 repo。
- 回歸測試：執行完整 `pytest`、`compileall`、`pip check` 與 `git diff --check`。
- E2E：本機 MMIS 網路與有效 `.env` 可用時，以錄製工單執行 live CLI 並核對 stdout JSON；若未執行，列為殘留風險。
- 視覺：不適用。
- 安全檢查：搜尋瀏覽器依賴與敏感字樣；審查同源網路限制、錯誤訊息與輸入處理。

## 情境包（Context Pack）

- 任務：新增「以工作單號查詢日檢工單內容」HTTP-only CLI。
- 目標：工作單參數化，進入唯一工單，擷取故障通報管理並在 stdout 輸出可判空 JSON。
- 相關檔案：`src/mmis_connector/query_daily_inspection_work_orders.py`、`events.py`、`parser.py`、`cli.py`、`__init__.py`、`tests/`、指定錄製的 HAR／timeline／DOM。
- 既有模式：單一 `requests.Session`、動態 PageState、`MaximoEventClient`、CDATA flatten、依表頭解析動態 table prefix、stdout JSON。
- 假設：工作單查詢必須唯一且完全相符；明細空表仍會保留 `summary` 與表頭。
- 未知事項：實際 MMIS 空表 DOM 尚未錄製；工作單明細 click 回應是否直接含完整明細或需要跟隨額外導覽，需在實作時以 HAR 精確驗證；超過單頁的故障通報案例尚未錄製。
- 允許變更的檔案：上述 `src/mmis_connector/` 模組、對應 tests、本 Epic artifacts、看板、情境地圖，以及完成後的 MMIS 知識庫更新。
- 不得觸碰：`.env`、錄製檔案、外部 session evidence、無關功能與 UI。
- 驗證指令：`python -m pytest`、`python -m compileall -q src tests`、`python -m pip check`、`git diff --check`、安全字樣搜尋、條件允許時 live CLI。
- 風險等級：高。
- 情境預算備註：已讀專案／架構地圖、既有日檢查詢與 parser／CLI、MMIS 開發知識、指定錄製摘要、HAR 關鍵查詢事件與最終 DOM；略過無關靜態資源與其他 app 流量。完整 click response 與空表形態保留給核准後的實作階段精查。

## 待人工核准的決策

- 結果只印到 stdout，不建立 JSON 檔案，也不提供 `--output` 參數。
- 空表是成功結果；找不到工作單則是錯誤結果。
- 對多筆或非完全相符結果一律 fail closed，不自動選第一筆。
