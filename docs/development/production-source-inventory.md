# Production Source Inventory

這份 inventory 以 `AutoLinkUnprocessedFaultNotices` 的實際 import、物件建構與方法呼叫為
依據，不以檔名中的 `query`、`read` 或 `link` 判斷 module 定位。

## `src/mmis_connector/` 全檔案分類

| Module | 分類 | Auto-link 關係 | 最終位置與理由 |
|---|---|---|---|
| `__init__.py` | B：正式 package public API | 匯出 application、reusable components 與 infrastructure | 保留；沒有 development-only export |
| `__main__.py` | A：Production entry point | 啟動正式 `cli.main` | 保留 |
| `auth.py` | B：共用基礎設施 | 所有 Query／Reader／Linker／transport 使用 session、page state 與安全例外 | 保留 |
| `events.py` | B：共用基礎設施 | 三個 MMIS service component 間接使用 app switching 與 event POST | 保留 |
| `parser.py` | B：共用基礎設施 | Query／Reader／Linker 皆依賴動態表格、分頁與 controls parsing | 保留 |
| `cli.py` | A：Production entry point | 只 dispatch auto-link production command | 保留 |
| `fault_notices/__init__.py` | B：domain package boundary | 標示 fault-notice domain；不擴張 root public API | 保留 |
| `fault_notices/query.py` | A：Auto-link 必要／共用 Query | Orchestrator 直接以 `UnprocessedFaultNoticeQuery` 載入 source snapshot；development tool 使用 `UnclosedFaultNoticeQuery` | 保留；兩者共用 app、saved-query 與分頁協定 |
| `fault_notices/reader.py` | B：正式共用 Reader | Auto-link 不使用；development tool 呼叫 `FaultNoticeAnalysisReader` | 保留；封裝可重用的唯一篩選、明細導航、semantic parsing 與驗證，wrapper 不得實作 domain logic |
| `daily_inspection/__init__.py` | B：domain package boundary | 標示 daily-inspection domain；不擴張 root public API | 保留 |
| `daily_inspection/query.py` | A：Auto-link 必要 | Orchestrator 直接以 `DailyInspectionWorkOrderQuery` 搜尋後續工單；Reader 亦重用 `open_all_records` | 保留 |
| `daily_inspection/reader.py` | A：Auto-link 間接必要 | Production Linker 建構 `DailyInspectionWorkOrderDetailReader`，呼叫 `open_detail()`，並重用 fault-table schema | 保留 |
| `daily_inspection/linker.py` | A：Auto-link 必要 | Orchestrator 直接以 `DailyInspectionWorkOrderFaultNoticeLinker` 執行 mutation 與 verification | 保留 |
| `auto_link/__init__.py` | B：application package boundary | 標示 auto-link application；不擴張 root public API | 保留 |
| `auto_link/orchestrator.py` | A：Production application | 正式 orchestrator 與 business rules | 保留 |
| `auto_link/store.py` | A：Auto-link 必要 | Orchestrator 直接使用 SQLite batch state | 保留 |

結論：目前沒有 C 類（只供 development tools 使用）的 source module，也沒有 Recorder、
standalone script、argument parser 或 debug output 混在 production service modules 中。

## 歷史 module 到 domain module 的 mapping

| 歷史 module | 現行 module | Auto-link 是否需要 | Production 使用路徑 | Development tool 是否使用 |
|---|---|---|---|---|
| `query_unprocessed_fault_notices.py` | `fault_notices/query.py` | 是，直接 | `source_query_factory` → `UnprocessedFaultNoticeQuery.run()` | 是 |
| `query_daily_inspection_work_orders_by_vehicle_and_date.py` | `daily_inspection/query.py` | 是，直接且間接 | Orchestrator → `run()`；DetailReader → `open_all_records()` | 是 |
| `query_fault_notices_linked_to_daily_inspection_work_order_by_number.py` | `daily_inspection/reader.py` | 是，間接 | Linker → `DailyInspectionWorkOrderDetailReader.open_detail()` 與 fault-table schema | 是 |
| `link_fault_notice_to_daily_inspection_work_order_by_number.py` | `daily_inspection/linker.py` | 是，直接 | Orchestrator → `DailyInspectionWorkOrderFaultNoticeLinker.run()` | 是 |

另外兩個 application module 已由 `auto_link_unprocessed_fault_notices_to_daily_inspection_work_orders.py`
與 `auto_link_store.py` 分別實體移至 `auto_link/orchestrator.py` 與 `auto_link/store.py`。
舊 internal module files 已移除，未保留 forwarding shim；穩定相容面是 root
`mmis_connector` 的 package-level exports 與 user-facing CLI commands。

## Mixed-code 審核

四個 domain service module 均未包含 `sys.argv`、argument parsing、stdout printing、JSON shell、subprocess、
Recorder evidence path 或 `tools` import。Development-facing executable 行為已完全位於
`tools/mmis_development/`。

`DailyInspectionWorkOrderDetailReader.run()` 目前由 development tool 使用，但仍屬正式
domain Reader API：它組合 `open_detail()`、fault-table parsing、空表語義與分頁 fail-closed。
把這段移到 tools 會複製或下放正式 parser／validation orchestration；同一 class 的
`open_detail()` 又是 Production Linker 的必要依賴，因此不做拆分。

`FaultNoticeAnalysisReader` 亦是正式 domain Reader API；它組合業務鍵驗證、
Maximo event 導航與故障分析表單的 semantic parsing。雖目前只有 development tool
呼叫，若移入 tools 會使後續 application 必須反向依賴 executable wrapper 或複製協定邏輯。

## `__init__.py` export 審核

保留以下 export：

- `AutoLinkUnprocessedFaultNotices`：Production application。
- `UnprocessedFaultNoticeQuery`、`DailyInspectionWorkOrderQuery`、
  `DailyInspectionWorkOrderDetailReader`、`DailyInspectionWorkOrderFaultNoticeLinker`：
  auto-link 直接或間接依賴的正式 domain services。
- `UnclosedFaultNoticeQuery`：正式的唯讀 fault-notice Query，由 development tool 提供人工入口。
- `FaultNoticeAnalysisReader`：正式的唯讀 fault-notice Reader，由 development tool 提供人工入口。
- `MMISConfig`、`MMISSession`、`PageState`、`MMISClientError`：共用 infrastructure。

目前沒有只代表 development executable wrapper 的 export；tools modules 不由 package
`__init__.py` 匯出。

## 依賴方向

```text
Production CLI
  ↓
AutoLinkUnprocessedFaultNotices
  ├─ UnprocessedFaultNoticeQuery
  ├─ DailyInspectionWorkOrderQuery
  ├─ DailyInspectionWorkOrderFaultNoticeLinker
  │   └─ DailyInspectionWorkOrderDetailReader
  └─ AutoLinkStore
       ↓
MaximoEventClient / parser / MMISSession
```

```text
Development tools
  ↓
同一組 Production Query / Reader / Linker
  ↓
MaximoEventClient / parser / MMISSession
```

Production 不得 import `tools/mmis_development/`；此邊界由
`tests/test_architecture.py` 保護。
