# MMIS 功能開發與已驗證元件指南

這份文件是新增 MMIS／IBM Maximo 功能前的搜尋入口。正式 runtime code 只放在
`src/mmis_connector/`；錄製證據、探索腳本與最小單一操作不得成為 production
dependency。

## 先搜尋，再錄製

開始新的 MMIS 功能前，依序搜尋：

1. `src/mmis_connector/` 的公開 Query、Reader、Linker、transport、parser 與驗證函式。
2. `tests/` 的 event sequence、錯誤路徑、recorded DOM 測試與 mock 用法。
3. 本文件的已驗證操作索引，以及 `ai/context/code-search-guide.md`。
4. 確認沒有可重用實作後，才用 Recorder 建立新的受控證據。

建議搜尋命令：

```powershell
rg -n "MMISSession|MaximoEventClient|Query|Reader|Linker|parse_|post_events|load_app" src tests
rg -n "APPID|PAGESEQNUM|UISESSIONID|CSRFTOKEN|table_summary|required_headers" src tests
```

## 開發生命週期

```text
Recorder 錄製
    ↓
HTTP / Maximo event 與 page state 分析
    ↓
Development Tool
    ↓
離線測試與受控 Live 驗證
    ↓
Reusable Query / Reader / Linker / parser / transport
    ↓
Production Application / Orchestrator
```

必須遵守以下依賴方向：

```text
Production CLI → Application / Orchestrator ─┐
                                             ├→ Reusable MMIS components
Development Tools ───────────────────────────┘
  ↓
MaximoEventClient
  ↓
MMISSession
```

- Production CLI 只處理 production application 的參數、dispatch、exit code 與 JSON stdout。
- Development tools 位於 `tools/mmis_development/`，只處理 arguments、正式 component 呼叫與 JSON output。
- Production code 不得 import CLI handler，也不得用 subprocess 呼叫另一個 CLI。
- Production code 不得 import `tools/`、development tools 或 reference scripts。
- Recorder evidence 與 development/reference script 不得成為 runtime dependency。
- 驗證成功且可共用的 protocol、解析或 domain logic 應移入正式 package，不能留在
  reference script 供 production 呼叫。
- 不重新實作已存在的 Maximo protocol；先擴充既有 component 或 parser。
- 整合完成後，刪除無參考價值的臨時檔；仍有教學或協定價值的內容才保留為
  development reference，並移除憑證、cookie、token、session ID 與內部資料。

## 已驗證 reusable components

| 能力 | 正式元件 | 已驗證重點 |
|---|---|---|
| 登入與 shared session | `auth.MMISSession` | login form、同源 HTTPS、GET-only retry、page state |
| Page state | `auth.PageState`、`auth.parse_page_state` | `PAGESEQNUM`、`UISESSIONID`、CSRF token、app ID |
| Maximo event 與 app switching | `events.MaximoEventClient` | `maximo.jsp`、Referer、sequence header、CDATA redirect、shared-session failure |
| 未處理通報查詢 | `fault_notices.query.UnprocessedFaultNoticeQuery` | saved query 比較、dynamic table、pagination、一致性檢查 |
| 未結案通報查詢 | `fault_notices.query.UnclosedFaultNoticeQuery` | 固定 depot／A、B 級 filter、dynamic table、完整 pagination |
| 日檢工單查詢 | `daily_inspection.query.DailyInspectionWorkOrderQuery` | 固定條件、日期運算子、dynamic table、單頁 fail-closed |
| 工單明細 | `daily_inspection.reader.DailyInspectionWorkOrderDetailReader` | 唯一工作單、進入明細、故障通報表格 |
| 故障通報勾稽 | `daily_inspection.linker.DailyInspectionWorkOrderFaultNoticeLinker` | dynamic controls、單一 multi-event POST、mutation verification、不確定結果不重送 |
| XML／CDATA 與表格解析 | `parser` | table summary、dynamic prefix、checkbox、多行文字、pagination |
| 自動勾稽批次狀態 | `auto_link.store.AutoLinkStore` | SQLite、resume、每筆 commit、`linking`／`link_error`、execution lock |
| 正式批次編排 | `auto_link.orchestrator.AutoLinkUnprocessedFaultNotices` | shared session、車號正規化、唯一工單、fail-closed、JSON summary |

這些 module 是 production implementation，不是因為最初由部分功能驗證而產生就視為
舊程式。五個單一操作 development tools 是它們的人工入口，並同時提供 debugging、行為確認、
受控 Live 驗證與單筆操作價值。

| Development tool | Tool 建構的正式元件 | 與 auto-link 的關係 |
|---|---|---|
| `tools.mmis_development.query_unprocessed_fault_notices` | `UnprocessedFaultNoticeQuery` | Auto-link 直接重用同一 class，不呼叫 tool |
| `tools.mmis_development.query_unclosed_fault_notices` | `UnclosedFaultNoticeQuery` | 獨立唯讀診斷操作；不由 Auto-link 呼叫 |
| `tools.mmis_development.query_daily_inspection_work_orders_by_vehicle_and_date` | `DailyInspectionWorkOrderQuery` | Auto-link 直接重用同一 class，不呼叫 tool |
| `tools.mmis_development.query_daily_inspection_work_order_by_number` | `DailyInspectionWorkOrderDetailReader` | Auto-link 的 Linker 間接重用 Reader，不呼叫 tool |
| `tools.mmis_development.query_daily_inspection_work_order_by_number_and_link_fault_notice` | `DailyInspectionWorkOrderFaultNoticeLinker` | Auto-link 直接重用同一 class，不呼叫 tool |

## Reference 與 evidence 的存放規則

目前 repository 內沒有需要搬移的 Recorder 衍生 runtime script。錄製 DOM 測試使用本機
外部 `maximoFlowRecorder/recordings`，不存在時以 optional test skip；HAR、session evidence
與內部資料不得提交。

未來依內容放置：

```text
src/mmis_connector/       正式 runtime 與 reusable components
tests/                    單元、整合、mock 與可安全提交的最小 fixture
docs/development/         無敏感資料的協定說明、已驗證操作索引與開發指南
ai/artifacts/             規格、任務卡與驗證報告，不作 runtime dependency
tools/kanban/             專案治理資料，不作 runtime dependency
tools/mmis_development/   可執行的 MMIS development／diagnostic wrappers
data/                     本機 runtime state；SQLite 由 .gitignore 排除
```

新的可執行探索工具放在 `tools/mmis_development/`；每個工具必須標示是否會 mutation、
使用的正式元件，以及「不得由 production import」。完成使命後，有 debugging／reference
價值者保留，無價值者刪除 wrapper；reusable implementation 永遠回到正式 package。

Production source 依 domain package 組織：

```text
fault_notices/
  query.py
daily_inspection/
  query.py
  reader.py
  linker.py
auto_link/
  orchestrator.py
  store.py
```

新正式 module 應優先使用 `domain/query.py`、`domain/reader.py`、`domain/linker.py` 等
responsibility 名稱，不要持續增加 `query_<完整 CLI 操作描述>.py`。Development tool 是可執行
操作入口，保留完整、明確的操作式檔名是合理的；它仍只能 import Production domain
components，Production 不得反向依賴 tool。

## Auto-link 的實際 dependency graph

```text
cli._auto_link_unprocessed_fault_notices
  ├─ MMISConfig → MMISSession
  ├─ AutoLinkStore → sqlite3
  └─ AutoLinkUnprocessedFaultNotices
      ├─ UnprocessedFaultNoticeQuery
      │   ├─ MaximoEventClient → MMISSession
      │   └─ parser
      ├─ DailyInspectionWorkOrderQuery
      │   ├─ MaximoEventClient → MMISSession
      │   └─ parser
      ├─ DailyInspectionWorkOrderFaultNoticeLinker
      │   ├─ DailyInspectionWorkOrderDetailReader
      │   │   ├─ DailyInspectionWorkOrderQuery
      │   │   └─ parser
      │   ├─ MaximoEventClient → MMISSession
      │   └─ parser
      └─ AutoLinkStore
```

Auto-link 不依賴五個 development tools；它們共同使用上表的正式 Python components。
這個邊界由 `tests/test_architecture.py` 的 import graph 與 production import boundary 測試保護。

`src/mmis_connector/` 的逐檔分類、四個歷史功能 module 的直接／間接使用證據與
`__init__.py` export 審核，見 `docs/development/production-source-inventory.md`。
