# MMIS Connector

MMIS Connector 是一個不依賴瀏覽器的 Python 命令列工具。它使用純 HTTP 流程登入 MMIS，從首頁進入「故障通報管理」，套用「本段未處理通報(車輛配屬段)」儲存查詢，最後將畫面資料以 JSON 輸出至命令列。

## 功能

- 使用 `requests.Session` 登入並在單次執行期間保持登入狀態。
- 從登入頁解析 hidden fields，不寫死動態 token。
- 重播 Maximo `maximo.jsp` event request，不使用 Playwright、Selenium 或其他瀏覽器。
- 自動進入 `ZZ_FNM` 故障通報管理並套用指定儲存查詢。
- 解析 Maximo XML／CDATA 回應中的完整結果表格。
- 支援空欄位、checkbox 與零筆結果。
- 成功或失敗皆輸出可解析的 UTF-8 JSON。
- 不在 JSON 中輸出密碼、cookie、CSRF token 或 session ID。

## 執行流程

```text
.env
  ↓
MMISSession 登入並保持 requests.Session
  ↓
載入 MMIS 首頁／啟動中心
  ↓
changeapp(ZZ_FNM)
  ↓
開啟儲存查詢選單
  ↓
套用「本段未處理通報(車輛配屬段)」
  ↓
解析表格並輸出 JSON
```

程式分成兩個主要部分：

- `src/mmis_connector/auth.py`：讀取設定、登入 MMIS、保存 cookies 與最新 page state。
- `src/mmis_connector/query_unprocessed_fault_notices.py`：從首頁切換應用程式、套用「本段未處理通報(車輛配屬段)」查詢並取得結果。

其他模組：

- `src/mmis_connector/parser.py`：解析 Maximo XML／CDATA 與故障通報表格。
- `src/mmis_connector/cli.py`：組合完整流程、處理 exit code 並輸出 JSON。

## 功能模組命名規則

MMIS 功能模組使用 `動作_領域物件.py`，避免使用無法辨識實際用途的 `workflow.py`、`handler.py` 或 `utils.py`：

| 功能類型 | 模組格式 | 類別格式 | 範例 |
|---|---|---|---|
| 查詢清單 | `query_<domain_objects>.py` | `<DomainObject>Query` | `query_unprocessed_fault_notices.py`／`UnprocessedFaultNoticeQuery` |
| 讀取單筆內容 | `read_<domain_object>_detail.py` | `<DomainObject>DetailReader` | `read_fault_notice_detail.py`／`FaultNoticeDetailReader` |
| 執行動作 | `<verb>_<domain_object>.py` | `<DomainObject><Action>` | `close_fault_notice.py`／`FaultNoticeCloser` |

未來功能建議命名：

- 讀取特定故障通報內容：`read_fault_notice_detail.py`／`FaultNoticeDetailReader`
- 查詢「動力車日檢(1A)」清單：`query_one_a_work_orders.py`／`OneAWorkOrderQuery`

共用的登入、HTTP transport 與 page state 留在 `auth.py`；跨功能共用的解析能力留在具體命名的 parser 模組。每個功能模組只負責一個可獨立描述與測試的 MMIS 操作。

## 系統需求

- Windows
- Python 3.11 或更新版本
- 可連線至 MMIS 內部網站
- 具有「故障通報管理」及目標儲存查詢權限的 MMIS 帳號

## 安裝

在專案目錄執行：

```powershell
cd C:\Docker\mmisConnector
python -m pip install -e ".[test]"
```

此指令會安裝 `requests`、`beautifulsoup4`、`python-dotenv` 與 `pytest`。

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

`.env` 已列入 `.gitignore`，不得提交到 Git。`.env.example` 只能保留空白或示範值。

### SSL 憑證注意事項

安全預設為 `MMIS_VERIFY_SSL=true`。如果目前 Python trust store 沒有機關內部 CA，執行時可能出現 `SSLError`。只有在確認連線目標及網路環境可信時，才暫時改為：

```dotenv
MMIS_VERIFY_SSL=false
```

長期建議是將機關 CA 加入受信任憑證鏈，再恢復 SSL 驗證。

## 執行

使用 Python module 與功能子命令：

```powershell
python -m mmis_connector query-unprocessed-fault-notices
```

安裝完成後也可以使用 console command：

```powershell
mmis-connector query-unprocessed-fault-notices
```

程式只在 stdout 輸出 JSON，方便 PowerShell 或其他程式接續處理：

```powershell
$result = python -m mmis_connector query-unprocessed-fault-notices | ConvertFrom-Json
$result.count
$result.records
```

子命令同樣採「動作 + 領域物件」命名。未來可擴充為：

```powershell
mmis-connector read-fault-notice-detail --notice-number <通報號>
mmis-connector query-one-a-work-orders
```

上述兩個未來指令目前尚未實作。

## JSON 輸出

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

目前每筆資料包含 17 個欄位：車次、車組/車號、發生日期、發生時間、事故等級、故障地點、ATP故障、故障現象、立案人員、通報人員、通報單位、通報股室、狀態、通報號、配屬段別、配屬段別名稱、顏色查詢。

查無資料時，`count` 為 `0` 且 `records` 為空陣列。

失敗時 exit code 為 `1`：

```json
{
  "success": false,
  "error": "MMISClientError",
  "message": "安全且不包含憑證或 session 資訊的錯誤訊息"
}
```

## 測試

執行全部測試：

```powershell
python -m pytest
```

執行語法與依賴完整性檢查：

```powershell
python -m compileall -q src tests
python -m pip check
```

測試涵蓋 page state 解析、缺少必要狀態時的錯誤處理、跨來源 URL 阻擋、空結果，以及錄製 DOM 的 16 筆／17 欄回歸驗證。

錄製 DOM 測試目前讀取：

```text
C:\Docker\maximoFlowRecorder\recordings\2026-09-21_login\dom\2026-09-21T054259-270.html
```

預設 pytest 不會登入或修改 MMIS。實際 HTTP 流程需另外執行 `python -m mmis_connector query-unprocessed-fault-notices` 驗證。

## 安全性

- 不要提交 `.env`、HAR、session evidence、cookie 或 token。
- 不要將完整成功 JSON 貼到公開 issue；故障通報可能包含內部或個人資料。
- HTTP client 會拒絕與 `MMIS_BASE_URL` 不同來源的 form action 及 redirect。
- POST request 不會由 transport layer 自動重送，避免重播登入或 Maximo event。
- 登入狀態只存在目前程序記憶體；程式結束後不保存 session cookie。

## 常見問題

### `.env 缺少 MMIS_USERNAME 或 MMIS_PASSWORD`

確認 `.env` 位於專案根目錄，且兩個欄位都有設定。

### `MMIS 登入失敗`

確認帳密有效、帳號未鎖定，並確認目前網路可以存取 MMIS。

### `SSLError`

優先安裝正確的內部 CA；僅在受信任環境中暫時設定 `MMIS_VERIFY_SSL=false`。

### `MMIS session 拒絕 event`

重新執行命令，讓程式建立新的 Session。若持續發生，可能是 Maximo 的 page sequence 或 event protocol 已改版。

### `查詢回應找不到故障通報表頭`

可能是 MMIS 表格 DOM、應用程式 ID 或儲存查詢名稱已變更，需要重新錄製流程並更新 parser／event constants。

## 已知限制

- 目前只支援「本段未處理通報(車輛配屬段)」。
- 沒有跨程序 session cache；每次執行都會重新登入。
- Maximo app ID、event target ID 與表格欄位規律若改版，需要同步更新程式。
- 不下載 Excel，也不包含排程、圖形介面或瀏覽器 fallback。
