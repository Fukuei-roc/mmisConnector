# MMIS Connector

MMIS Connector 是一套不依賴瀏覽器的 Python 命令列工具。它使用 `requests.Session` 登入 MMIS，重播 Maximo HTTP event，解析 XML／CDATA 中的表格資料，並將結果輸出為 UTF-8 JSON。

目前提供三項功能：

| 功能 | CLI 子命令 | 輸入 |
|---|---|---|
| 比較並查詢本段未處理故障通報 | `query-unprocessed-fault-notices` | 無 |
| 查詢動力車日檢(1A)工單 | `query-daily-inspection-work-orders` | 車組／車號、檢修日期 |
| 以工作單號查詢日檢工單內容 | `query-daily-inspection-work-order-by-number` | 工作單號 |

## 功能特色

- 使用既有 MMIS 表單登入流程，不需要 Playwright、Selenium 或 Chrome。
- 以單一 `requests.Session` 保存程序執行期間的 cookie 與 page state。
- 從 MMIS 回應解析 `PAGESEQNUM`、`UISESSIONID`、CSRF token 與 app ID，不在原始碼寫死動態值。
- 共用 Maximo `maximo.jsp` event transport 與 app 切換流程。
- 解析 Maximo XML／CDATA、動態表格 ID、文字欄位與 checkbox。
- 依序比較「未處理故障通報(車輛配屬段)」與「未處理故障通報(開單時所屬段)」，擷取筆數較多者；平手時優先車輛配屬段。
- 支援選定故障通報的多頁結果擷取與筆數一致性檢查。
- 日檢工單支援合法日期驗證、空結果及不完整結果保護。
- 可依工作單號進入唯一日檢工單，擷取「故障通報管理」，並明確區分空表與解析失敗。
- 成功與失敗皆輸出可解析 JSON；不輸出密碼、cookie、CSRF token 或 session ID。
- 所有功能只將 JSON 輸出至 stdout，不建立結果檔案。

## 系統需求

- Windows
- Python 3.11 或更新版本
- 可連線至 MMIS 內部網站
- 具有對應 MMIS 應用程式與資料的存取權限

## 安裝

在專案目錄執行：

```powershell
cd C:\Docker\mmisConnector
python -m pip install -e ".[test]"
```

主要依賴：`requests`、`beautifulsoup4`、`python-dotenv`，以及測試用的 `pytest`。

## 環境設定

複製範例設定：

```powershell
Copy-Item .env.example .env
```

編輯 `.env`：

```dotenv
MMIS_USERNAME=你的帳號
MMIS_PASSWORD=你的密碼
MMIS_BASE_URL=https://ap.nmmis.railway.gov.tw
MMIS_VERIFY_SSL=true
MMIS_TIMEOUT_SECONDS=20
```

| 變數 | 必填 | 預設值 | 說明 |
|---|---:|---|---|
| `MMIS_USERNAME` | 是 | 無 | MMIS 登入帳號 |
| `MMIS_PASSWORD` | 是 | 無 | MMIS 登入密碼 |
| `MMIS_BASE_URL` | 否 | `https://ap.nmmis.railway.gov.tw` | MMIS HTTPS 根網址 |
| `MMIS_VERIFY_SSL` | 否 | `true` | 是否驗證伺服器 TLS 憑證 |
| `MMIS_TIMEOUT_SECONDS` | 否 | `20` | 單次 HTTP request 逾時秒數，必須大於 0 |

`.env` 已列入 `.gitignore`，不得提交到 Git；`.env.example` 只能保留空白或示範值。

### SSL 憑證

安全預設為 `MMIS_VERIFY_SSL=true`。如果 Python trust store 沒有機關內部 CA，執行時可能出現 `SSLError`。只有在確認連線目標與網路環境可信時，才可暫時設定：

```dotenv
MMIS_VERIFY_SSL=false
```

長期做法應是安裝正確的機關 CA，並恢復 TLS 憑證驗證。

## 使用方式

可以使用 Python module：

```powershell
python -m mmis_connector <子命令> [參數]
```

安裝完成後也可以使用 console command：

```powershell
mmis-connector <子命令> [參數]
```

### 查詢本段未處理故障通報

```powershell
python -m mmis_connector query-unprocessed-fault-notices
```

此功能會：

1. 登入 MMIS 並載入啟動中心。
2. 進入 `ZZ_FNM`「故障通報管理」。
3. 依序套用「本段未處理通報(車輛配屬段)」與「本段未處理通報(開單時所屬段)」。
4. 比較兩個查詢的總筆數，選擇筆數較多者；筆數相同時選擇車輛配屬段。
5. 若選擇車輛配屬段，在比較完成後重新切回該查詢，確保後續分頁狀態正確。
6. 依選定查詢的表格分頁控制逐頁取得所有結果。
7. 驗證每頁範圍、總筆數與合併筆數後輸出 JSON。

PowerShell 使用範例：

```powershell
$result = python -m mmis_connector query-unprocessed-fault-notices |
  ConvertFrom-Json

$result.count
$result.records
```

### 查詢日檢工單

```powershell
python -m mmis_connector query-daily-inspection-work-orders 703 2026/09/22
```

參數順序：

1. `車組/車號`：trim 後不得為空白，例如 `703`。
2. `檢修日期`：有效的 `YYYY/MM/DD` 或 `YYYY/M/D` 日期。

此功能會：

1. 登入 MMIS 並進入 `ZZ_PMWO1A`「動力車日檢(1A)」。
2. 切換為「所有記錄」。
3. 使用固定條件 `檢修段=新竹機務段`。
4. 將車組／車號填入對應的 Maximo 查詢欄位。
5. 將日期正規化後，以 `>YYYY/MM/DD` 作為檢修日期條件。
6. 輸出工單清單；沒有資料時輸出「找不到對應工單」。

例如輸入 `2026/9/2` 時，JSON 的 `inspection_date` 會是 `2026/09/02`，送往 MMIS 的查詢條件則是 `>2026/09/02`。

PowerShell 使用範例：

```powershell
$result = python -m mmis_connector `
  query-daily-inspection-work-orders 703 2026/09/22 |
  ConvertFrom-Json

if ($result.count -eq 0) {
  $result.message
} else {
  $result.records | Select-Object '工作單', '車組/車號', '檢修日期'
}
```

### 以工作單號查詢日檢工單內容

```powershell
python -m mmis_connector `
  query-daily-inspection-work-order-by-number 115-1A-70048
```

唯一參數 `工作單號` 會先移除前後空白，且只能包含英文字母、數字與連字號。

此功能會：

1. 登入 MMIS 並進入 `ZZ_PMWO1A`「動力車日檢(1A)」。
2. 切換為「所有記錄」。
3. 以工作單欄位查詢指定工作單號。
4. 確認查詢結果恰好一筆，且工作單號與輸入完全相符。
5. 以 HTTP event 進入工單內容，不啟動瀏覽器。
6. 擷取「故障通報管理」的故障通報號、發生日期、車組／車號與故障現象。
7. 將儲存格內的多行故障現象轉成含換行字元的 JSON 字串。

PowerShell 判斷空資料範例：

```powershell
$result = python -m mmis_connector `
  query-daily-inspection-work-order-by-number 115-1A-70048 |
  ConvertFrom-Json

if (-not $result.has_fault_notices) {
  "此工單沒有故障通報資料"
} else {
  $result.records | Select-Object '故障通報號', '發生日期', '車組/車號', '故障現象'
}
```

結果只會印到 stdout，不會建立 JSON 或其他結果檔案。找不到工作單、命中多筆或結果不完全相符時會安全失敗，不會自行選擇第一筆。

## JSON 輸出

### 未處理故障通報成功結果

成功時 exit code 為 `0`：

```json
{
  "success": true,
  "query_name": "本段未處理通報(車輛配屬段)",
  "count": 1,
  "records": [
    {
      "車次": "範例",
      "車組/車號": "範例",
      "發生日期": "2026/09/21",
      "發生時間": "12:34",
      "事故等級": "C",
      "故障地點": "範例",
      "ATP故障": false,
      "故障現象": "範例",
      "立案人員": "範例",
      "通報人員": "範例",
      "通報單位": "範例",
      "通報股室": "範例",
      "狀態": "立案",
      "通報號": "範例",
      "配屬段別": "範例",
      "配屬段別名稱": "範例",
      "顏色查詢": ""
    }
  ]
}
```

查無資料時，`count` 為 `0`，且 `records` 為空陣列。

`query_name` 會是實際選定的查詢名稱：「本段未處理通報(車輛配屬段)」或「本段未處理通報(開單時所屬段)」。其他輸出鍵與 `records` 欄位格式不變。

### 日檢工單成功結果

```json
{
  "success": true,
  "query_name": "查詢日檢工單",
  "vehicle": "703",
  "inspection_date": "2026/09/22",
  "count": 1,
  "records": [
    {
      "檢修段": "新竹機務段",
      "配屬段": "新竹機務段",
      "車組/車號": "EMU703",
      "檢修級別": "1A",
      "工作單": "115-1A-範例",
      "車次": "範例",
      "檢修單位": "範例",
      "工作單狀態": "範例",
      "處理人員": "範例",
      "預計檢修(進廠)日": "2026/09/24",
      "檢修日期": "2026/09/23",
      "完工日期": "2026/09/23",
      "階段核簽人": "",
      "逾期標註?": false
    }
  ]
}
```

日檢工單查無資料時仍是成功的業務結果，exit code 為 `0`：

```json
{
  "success": true,
  "query_name": "查詢日檢工單",
  "vehicle": "999999",
  "inspection_date": "2099/12/31",
  "count": 0,
  "records": [],
  "message": "找不到對應工單"
}
```

### 日檢工單內容成功結果

有故障通報資料時，exit code 為 `0`：

```json
{
  "success": true,
  "query_name": "以工作單號查詢日檢工單內容",
  "work_order": "115-1A-70048",
  "has_fault_notices": true,
  "count": 1,
  "records": [
    {
      "故障通報號": "範例通報號",
      "發生日期": "2026/09/23",
      "車組/車號": "範例車號",
      "故障現象": "第一行故障現象\n第二行故障現象"
    }
  ]
}
```

「故障通報管理」表格存在但沒有資料列時，仍是成功的業務結果，exit code 為 `0`：

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

後續程式應優先使用 `has_fault_notices` 判斷是否有資料，也可同時檢查 `count` 與 `records`。

### 失敗結果

參數、登入、網路、MMIS event 或解析失敗時，exit code 為 `1`：

```json
{
  "success": false,
  "error": "MMISClientError",
  "message": "安全且不包含憑證或 session 資訊的錯誤訊息"
}
```

未預期例外不會將原始例外細節輸出到 stdout，以降低敏感資料外洩風險。

## 程式架構

```text
CLI 參數
  ↓
MMISConfig / MMISSession
  ↓
MaximoEventClient
  ↓
功能 Query 模組
  ↓
Maximo table parser
  ↓
JSON stdout
```

| 模組 | 職責 |
|---|---|
| `src/mmis_connector/auth.py` | 讀取 `.env`、登入、同源 HTTPS 檢查、保存 session 與 page state |
| `src/mmis_connector/events.py` | 共用 Maximo event POST、CSRF／sequence header、app 切換與 shared-session 錯誤偵測 |
| `src/mmis_connector/query_unprocessed_fault_notices.py` | 比較兩個未處理通報儲存查詢，並擷取選定結果的所有分頁 |
| `src/mmis_connector/query_daily_inspection_work_orders.py` | 驗證車號／日期，查詢動力車日檢(1A)工單 |
| `src/mmis_connector/read_daily_inspection_work_order.py` | 驗證工作單號、進入唯一日檢工單並擷取故障通報管理 |
| `src/mmis_connector/parser.py` | 展開 XML／CDATA、依 table summary 與動態 prefix 解析表頭、資料列、多行文字、checkbox 與分頁資訊 |
| `src/mmis_connector/cli.py` | 子命令 dispatch、參數數量檢查、exit code 與 JSON 輸出 |
| `src/mmis_connector/__init__.py` | 公開 Python API |

公開的主要 Python 類別：

- `MMISConfig`
- `MMISSession`
- `PageState`
- `UnprocessedFaultNoticeQuery`
- `DailyInspectionWorkOrderQuery`
- `DailyInspectionWorkOrderDetailReader`
- `MMISClientError`

查詢清單的功能模組採 `query_<domain_objects>.py` 命名，單筆內容讀取採 `read_<domain_object>.py`；登入與 transport 保持在共用模組，個別 Query／Reader 類別只負責一項 MMIS 操作的事件順序與領域規則。

## 測試與驗證

執行全部測試：

```powershell
python -m pytest
```

執行語法、依賴與 diff 檢查：

```powershell
python -m compileall -q src tests
python -m pip check
git diff --check
```

測試涵蓋：

- 設定與 page state 解析。
- HTTPS 同源網路邊界。
- Maximo event payload 與 shared-session 錯誤。
- 故障通報的雙查詢順序、較大筆數選擇、平手優先、空結果、多頁合併與分頁一致性。
- 日檢工單輸入正規化、event 順序、有資料、空結果與多頁保護。
- 工作單號驗證、唯一命中保護、明細點擊、故障通報空表、缺表、多行文字及未完整分頁保護。
- CLI 子命令與參數 dispatch。
- 本機錄製 DOM 存在時的離線解析回歸。

預設 pytest 不會登入 MMIS。Live 驗證需另外執行對應 CLI，並使用有效 `.env` 與內網連線。

## 安全性

- 不要提交 `.env`、HAR、session evidence、cookie、token 或包含內部資料的輸出檔。
- 不要將完整成功 JSON 貼到公開 issue；結果可能包含內部資料或個人資料。
- `MMISSession` 只允許與 `MMIS_BASE_URL` 相同 scheme 與 host 的請求。
- transport 只會自動重試 GET，不自動重送登入或 Maximo event POST。
- 登入狀態只存在目前程序記憶體，程式結束後不保存 session cookie。
- CLI 錯誤輸出不包含帳密、token、cookie、session ID 或完整 response body。

## 常見問題

### `.env 缺少 MMIS_USERNAME 或 MMIS_PASSWORD`

確認 `.env` 位於專案根目錄，且兩個欄位都有設定。

### `MMIS 登入失敗`

確認帳密有效、帳號未鎖定，並確認目前網路可以存取 MMIS。

### `SSLError`

優先安裝正確的內部 CA；僅在受信任環境中暫時設定 `MMIS_VERIFY_SSL=false`。

### `MMIS session 拒絕 event`

重新執行命令以建立新 Session。若持續發生，可能是 Maximo 的 page sequence 或 event protocol 已改版。

### `檢修日期必須是有效的 YYYY/MM/DD 日期`

使用真實日曆日期，例如 `2026/09/22`；`2026-09-22` 或 `2026/02/30` 都會被拒絕。

### `找不到對應工單`

這是有效的零筆結果，不是程式錯誤。請確認車組／車號、日期以及固定檢修段「新竹機務段」是否符合預期。

### `找不到工作單：...`

這是 `query-daily-inspection-work-order-by-number` 的錯誤結果。請確認工作單號正確；此命令只有在唯一命中且完全相符時才會進入工單，避免誤讀其他資料列。

### `工作單查詢結果不是唯一一筆`

查詢回應不是恰好一筆，或 MMIS 顯示的總筆數與目前資料列不一致。程式會安全停止，不會自行選擇第一筆。

### `故障通報管理結果超過單頁，拒絕回傳不完整資料`

目前工單明細 reader 不會靜默忽略後續頁面。若實際工單有超過一頁的故障通報，需要另行擴充明細分頁支援。

### `日檢工單結果超過單頁，拒絕回傳不完整資料`

目前日檢工單功能不會靜默忽略後續頁面。請縮小查詢條件，或另行擴充日檢工單分頁支援。

### `查詢回應找不到...`

MMIS 的表格欄名、app ID、event target 或 DOM 結構可能已變更，需要重新錄製流程並更新 parser 或功能模組。

## 已知限制

- 每次 CLI 執行都會重新登入，沒有跨程序 session cache。
- 日檢工單固定使用「新竹機務段」，目前沒有 depot CLI 參數。
- 日檢工單不擷取多頁；偵測到結果超過單頁時會明確失敗。
- 以工作單號讀取明細時，故障通報超過單頁會明確失敗，不會輸出不完整資料。
- Maximo app ID、欄位語義或 event protocol 改版時，需要同步更新程式。
- 不下載 Excel，也不包含排程、圖形介面或瀏覽器 fallback。
