# MMIS Connector

## Overview

MMIS Connector 是一個 Python CLI 專案，用來在不啟動瀏覽器的情況下執行已授權的
MMIS／IBM Maximo 操作。它透過 authenticated `requests.Session` 登入 MMIS、送出
Maximo HTTP event、維護 page state，並解析 HTML、XML／CDATA 與動態表格回應。

Repository 同時包含兩種入口：

- **Production Application**：正式批次工作流程，由 `mmis-connector` CLI 提供。
- **Development / Diagnostic Tools**：MMIS 探索、除錯、元件驗證與受控 Live 驗證工具，
  位於 `tools/mmis_development/`，不屬於正式 CLI。

## Production Features

目前正式 CLI 只提供一個 Production Application：

| 功能 | CLI command | 是否修改 MMIS |
|---|---|---:|
| 將本段未處理故障通報勾稽至適合的後續日檢工單 | `auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders` | 是 |

### Auto-link Unprocessed Fault Notices

Auto-link 以一個 MMIS session 查詢本段未處理故障通報，依每筆通報的車號與發生日期
搜尋後續動力車日檢（1A）工單。只有最早檢修日期對應唯一工作單時才會勾稽；同一最早
日期出現多張不同工單時，會記錄 `ambiguous_work_order`，不自行選擇。

目前批次安全契約：

- 使用 `data/auto_link_unprocessed_fault_notices.sqlite3` 保存來源 snapshot 與逐筆狀態。
- 有未完成批次時續跑原批次，不重新查詢正在變動的來源集合。
- 已完成批次會在下一次執行建立新批次前清除。
- 每筆狀態轉換立即 commit；查詢失敗可續跑，MMIS mutation 結果不明則不可自動重送。
- 寫入前先保存 `linking`；中斷或無法確認結果時轉為 `link_error`，必須人工核對。
- 寫入後會重新解析「故障通報管理」，確認指定故障通報確實存在，才視為成功。
- 日檢工單必須唯一且完全符合；多頁或無法完整驗證的結果採 fail-closed。
- 來源車號原值保留在 SQLite；查詢時移除非數字字元，首位為 `9` 的四位數車號會移除
  最後一位車廂碼，例如 `EP9393` 以 `939` 查詢。
- stdout 只輸出 JSON summary，包含 run ID、是否續跑、完成狀態、各結果計數、
  `link_error`、`manual_review_required` 與 database path，不輸出逐筆來源內容；其中
  `manual_review_required` 目前計算 `link_error`，歧義工單另由 `ambiguous_work_order` 呈現。

> 此 Production command 會修改 MMIS 資料。遇到 `link_error` 時不要刪除 SQLite、
> 修改狀態或直接重跑寫入；請先在 MMIS 人工確認實際結果。

## Installation

需求：

- Python 3.11 或更新版本
- 可連線至 MMIS 內部網站
- 具有目標 MMIS application 與資料的使用權限

在 repository root 安裝：

```powershell
python -m pip install -e ".[test]"
```

Runtime dependencies 為 `requests`、`beautifulsoup4` 與 `python-dotenv`；
`pytest` 由 `test` optional dependency 提供。

## Configuration

複製設定範例：

```powershell
Copy-Item .env.example .env
```

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
| `MMIS_BASE_URL` | 否 | `https://ap.nmmis.railway.gov.tw` | 必須是有效 HTTPS root URL |
| `MMIS_VERIFY_SSL` | 否 | `true` | 是否驗證 TLS 憑證 |
| `MMIS_TIMEOUT_SECONDS` | 否 | `20` | 單次 request timeout，必須大於 0 |

`.env` 已由 Git ignore 排除；`.env.example` 只保留空白或示範值。若內部 CA 尚未加入
Python trust store，應優先安裝正確 CA。只有在確認網路與目標可信時，才暫時使用
`MMIS_VERIFY_SSL=false`。

## Usage

### Production CLI

從 source checkout 執行：

```powershell
python -m mmis_connector `
  auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders
```

安裝 package 後也可使用 console entry point：

```powershell
mmis-connector auto-link-unprocessed-fault-notices-to-daily-inspection-work-orders
```

此 command 不接受額外參數。成功與失敗都輸出 UTF-8 JSON；成功 exit code 為 `0`，
參數、設定或執行錯誤的 exit code 為 `1`。個別批次資料列可能需要人工處理，因此
不能只看 process exit code；也要檢查 summary 的 `completed`、`failed`、
`ambiguous_work_order`、`link_error` 與 `manual_review_required`。

## Development / Diagnostic Tools

`tools/mmis_development/` 保存四個薄 executable wrappers，用於 MMIS 功能探索、
HTTP／Maximo event 行為確認、debugging、Production component 驗證、受控 Live validation
與人工單筆操作。它們直接重用 `src/mmis_connector/` 的正式 Query／Reader／Linker，
不由 Production CLI dispatch。

所有命令都從 repository root 執行：

| Tool | 用途 | 執行方式 | MMIS 影響 |
|---|---|---|---|
| 查詢未處理故障通報 | 驗證 saved query、table parsing 與 pagination | `python -m tools.mmis_development.query_unprocessed_fault_notices` | 唯讀 |
| 依車號與日期查詢日檢工單 | 驗證 filter、固定狀態與日期條件 | `python -m tools.mmis_development.query_daily_inspection_work_orders_by_vehicle_and_date 717 '>2026/09/23'` | 唯讀 |
| 依工作單號讀取明細 | 驗證唯一工單與故障通報表格 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number 115-1A-70048` | 唯讀 |
| 依工作單號勾稽故障通報 | 驗證 mutation 與結果確認 | `python -m tools.mmis_development.query_daily_inspection_work_order_by_number_and_link_fault_notice 115-1A-71002 1150923-36` | **會修改資料** |

最後一項只能在明確核准的受控 Live 驗證或人工單筆操作中使用。若 mutation 結果不明，
程式不會自動重送；必須先人工確認 MMIS。

完整參數、JSON contract 與安全說明見
[Development Tools README](tools/mmis_development/README.md)。

## Architecture

目前 Production source 依 domain responsibility 組織：

```text
src/mmis_connector/
├─ __init__.py
├─ __main__.py
├─ cli.py
├─ auth.py
├─ events.py
├─ parser.py
├─ fault_notices/
│  ├─ __init__.py
│  └─ query.py
├─ daily_inspection/
│  ├─ __init__.py
│  ├─ query.py
│  ├─ reader.py
│  └─ linker.py
└─ auto_link/
   ├─ __init__.py
   ├─ orchestrator.py
   └─ store.py
```

### Domain Packages

| 路徑 | 責任 |
|---|---|
| `fault_notices/query.py` | 查詢、比較並分頁擷取本段未處理故障通報 |
| `daily_inspection/query.py` | 依車號與日期條件查詢 1A 日檢工單 |
| `daily_inspection/reader.py` | 驗證唯一工作單並讀取工單明細與故障通報表格 |
| `daily_inspection/linker.py` | 勾稽指定故障通報並驗證 mutation 結果 |
| `auto_link/orchestrator.py` | 編排來源、工單選擇、逐筆處理與 JSON summary |
| `auto_link/store.py` | SQLite batch lifecycle、resume、逐筆狀態與 execution lock |
| `auth.py` | 設定、MMIS login、same-origin request boundary 與 page state |
| `events.py` | Maximo event POST、app switching 與 shared-session rejection detection |
| `parser.py` | XML／CDATA、動態 table、controls、checkbox 與 pagination parsing |
| `cli.py` | Production command 的參數、dispatch、JSON stdout 與 exit code |

### Dependency Direction

```text
Production CLI
      ↓
Auto-link Production Application
      ↓
Reusable Domain Components
      ↓
Maximo Event / Parser / MMISSession
      ↓
MMIS
```

```text
Development / Diagnostic Tools
              ↓
Reusable Domain Components
              ↓
Maximo Event / Parser / MMISSession
              ↓
MMIS
```

Development tools 可以重用 Production components；Production code 不得 import
`tools/mmis_development/`。這個方向與 auto-link dependency closure 由
`tests/test_architecture.py` 保護。

更完整的逐檔分類與 dependency graph 見
[Production Source Inventory](docs/development/production-source-inventory.md)。

### Public Python API

正式 package-level imports 由 `mmis_connector.__all__` 與 public API tests 保護：

```python
from mmis_connector import (
    AutoLinkUnprocessedFaultNotices,
    DailyInspectionWorkOrderDetailReader,
    DailyInspectionWorkOrderFaultNoticeLinker,
    DailyInspectionWorkOrderQuery,
    MMISClientError,
    MMISConfig,
    MMISSession,
    PageState,
    UnprocessedFaultNoticeQuery,
)
```

使用者程式應優先使用 package-level API，不要依賴歷史 internal module path。

## Development Workflow

新 MMIS 功能採以下生命週期：

```text
Recorder
  ↓
HTTP / Maximo event analysis
  ↓
Development Tool
  ↓
Offline tests / Controlled Live validation
  ↓
Reusable Domain Component
  ↓
Production Application
```

開始開發前，先搜尋現有 domain components、transport、parser 與 tests，避免重新實作
已驗證的 Maximo protocol。Recorder evidence 與 development scripts 不能成為 Production
runtime dependency。

命名原則：

- Development tool 描述「可執行什麼操作」，因此可以使用完整操作式名稱，例如
  `query_daily_inspection_work_order_by_number_and_link_fault_notice.py`。
- Production source 描述「component 負責什麼責任」，因此依 domain package 搭配
  `query.py`、`reader.py`、`linker.py`、`orchestrator.py`、`store.py` 組織。

完整搜尋順序、reference 規則與已驗證元件索引見
[MMIS Feature Development Workflow](docs/development/mmis-feature-workflow.md)。

## Testing

預設測試是離線測試，不登入或修改 MMIS：

```powershell
python -m pytest
```

截至 2026-09-29，本次實際 baseline 為：

```text
130 passed, 3 skipped
```

測試涵蓋 auth／page state、same-origin request、Maximo events、parser、Query／Reader／
Linker、SQLite resume 與 fail-closed、Production CLI、development tools、public API
及 architecture boundaries。

三個 skipped tests 使用 repository 外的 recorded DOM evidence。若本機存在對應錄製檔，
它們會執行離線解析回歸；缺少 evidence 時才 skip。它們不會連線 MMIS。

Live MMIS validation 不屬於預設 pytest，必須由人工明確選擇對應 command 並控制資料範圍；
mutation workflow 不應為了文件或一般 regression test 執行。

完整驗證指令：

```powershell
python -m pytest
python -m compileall -q src tests
python -m compileall -q tools/mmis_development
python -m pip check
git diff --check
```

## Safety and Security

- 帳號與密碼由環境變數或未追蹤的 `.env` 載入；原始碼與 `.env.example` 不保存真實值。
- Cookies、session 與 page state 保存在單次程序內的 `requests.Session`，沒有跨程序
  session cache。
- 所有 `MMISSession.request()` URL 都必須與 `MMIS_BASE_URL` 具有相同 scheme 與 host。
- TLS verification 預設啟用；`MMIS_BASE_URL` 必須使用 HTTPS。
- HTTP adapter 只自動 retry GET；登入 POST 與 Maximo event／mutation POST 不會由 transport
  自動 replay。
- CLI 與 development tools 對未預期例外使用通用錯誤訊息，避免把原始例外細節直接輸出。
- SQLite 會保存未處理通報來源與處理狀態；`data/*.sqlite3*` 已由 Git ignore 排除，但檔案
  本身不是加密儲存，應依內部資料規範保護本機目錄。
- 不要提交包含帳密、cookie、CSRF token、session ID 或內部資料的 HAR、錄製證據與輸出檔。
- 對任何 `link_error` 或 mutation 結果不明的狀態，先人工核對，不得直接重送。

## Known Limitations

- 每次獨立 CLI process 都會重新登入；auto-link 只在該次批次內重用同一 session。
- 日檢工單查詢固定使用「新竹機務段」與既定工作單狀態，沒有 depot CLI 參數。
- 日檢工單 query 與工單明細 reader 不會擷取多頁；偵測到不完整結果時會明確失敗。
- MMIS app ID、欄位語義、DOM 或 event protocol 改版時，需重新錄製並更新對應 component。
- 專案不下載 Excel，也不提供 scheduler、GUI 或 browser fallback。

## Development Documentation

- [Development Tools README](tools/mmis_development/README.md)：四個 diagnostic tools 的完整用法與 mutation 警示。
- [MMIS Feature Development Workflow](docs/development/mmis-feature-workflow.md)：Recorder 到 Production Application 的生命週期與重用規則。
- [Production Source Inventory](docs/development/production-source-inventory.md)：Production modules 分類、public API 與 dependency graph。
- [Architecture Map](ai/context/architecture-map.md)：MMIS session、transport、parser 與 application 邊界。
- [Code Search Guide](ai/context/code-search-guide.md)：新增或維護功能時的 source 搜尋入口。
