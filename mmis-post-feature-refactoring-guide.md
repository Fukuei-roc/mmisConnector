# MMIS Connector：功能完成後的 Production 收斂與架構整理指南

> 本文件供 Codex 在一個新的 MMIS 功能／主程式完成後使用。
>
> 目的不是重新設計已驗證的程式，而是把「開發過程中的小工具」與「完成後的正式 Production Application / reusable components」整理成一致、可長期維護的 repository 結構。

---

## 1. 核心原則

MMIS Connector 採用兩階段開發模式：

```text
探索／開發階段
Recorder
  ↓
HTTP / Maximo event 分析
  ↓
tools/mmis_development/ 下建立操作明確的小工具
  ↓
離線測試
  ↓
受控 Live 驗證
  ↓
逐步組合成完整主程式

功能完成後
Development Tools
  ↓
盤點與分類
  ↓
Reusable Components → 融入 src/mmis_connector/<domain>/
  ↓
Production Application → 保留正式入口／orchestrator
  ↓
Development / Diagnostic Tools → 留在 tools/mmis_development/
```

開發階段允許使用很長、描述完整操作的檔名，例如：

```text
tools/mmis_development/query_daily_inspection_work_order_by_number_and_link_fault_notice.py
```

這是刻意的。Development Tool 的檔名應優先描述「它可以執行什麼操作」，方便人工測試、除錯、Live 驗證及 Codex 搜尋。

但 Production source 不應永久沿用這種操作式長檔名。

當主程式完成後，正式 implementation 應依 domain responsibility 整理，例如：

```text
src/mmis_connector/
├─ fault_notices/
│  └─ query.py
├─ daily_inspection/
│  ├─ query.py
│  ├─ reader.py
│  └─ linker.py
└─ auto_link/
   ├─ orchestrator.py
   └─ store.py
```

---

## 2. Development Tools 與 Production Code 的定位

### `tools/mmis_development/`

用途：

- MMIS 功能探索
- Recorder 結果驗證
- HTTP / Maximo event 行為確認
- 單一功能測試
- debugging
- controlled Live validation
- 人工單筆操作
- 未來新功能的參考案例

Development Tool 可以：

- 使用完整操作式長檔名
- 有獨立 arguments
- 輸出 JSON
- 有獨立 exit code
- 直接 import Production reusable components

Development Tool 不應成為 Production Application 的 runtime dependency。

### `src/mmis_connector/`

只應包含：

1. Production Application
2. Production reusable components
3. 共用 infrastructure

不應包含：

- 純歷史實驗 script
- Recorder 衍生的一次性 script
- 僅供 debugging 的 wrapper
- 僅供 development tool 使用且沒有正式 reusable 價值的 implementation

---

## 3. 永久依賴規則

允許：

```text
Production Application ──────────┐
                                 ├→ Production Reusable Components
Development Tools ───────────────┘
                                      ↓
                             Maximo transport / parser
                                      ↓
                              MMISSession / auth
```

禁止：

```text
Production Application
        ↓
tools/mmis_development
```

也禁止 Production 透過 subprocess、CLI-to-CLI 或 shell command 呼叫 Development Tool。

---

## 4. 新功能開發期間的建議方式

開發新的 MMIS 功能時，不需要一開始就設計最終 Production package。

優先建立容易理解、容易驗證的小工具，例如：

```text
tools/mmis_development/
├─ query_xxx_by_vehicle_and_date.py
├─ query_xxx_by_number.py
├─ read_xxx_detail.py
├─ update_xxx_status.py
└─ link_xxx_to_yyy.py
```

每個工具只處理一個明確問題。

完成並驗證幾個小部分後，再組成主流程。

這個階段的目標是：

> 先確認 MMIS 實際行為，再決定正式 architecture。

不要為了提早追求漂亮架構，而在 Maximo protocol 尚未確認時過度抽象。

---

## 5. 主程式完成後的整理流程

當新的 Production Application 已完成並通過測試／必要的受控 Live 驗證後，執行以下整理。

### Step 1：建立實際 dependency graph

從正式主程式開始向下追蹤：

```text
Production CLI
  ↓
Production Application / Orchestrator
  ↓
Query / Reader / Linker / Service / Store
  ↓
MaximoEventClient / parser
  ↓
MMISSession / auth
```

不要依檔名猜測用途。

必須以實際 import 與 runtime dependency 判斷。

### Step 2：逐一分類開發期間產生的程式

每個 module / class / helper 分為：

#### A. Production Application 必要

主程式直接或間接使用。

→ 保留或移入 `src/mmis_connector/` 合適的 domain package。

#### B. 正式 reusable component

例如：

- Query
- Reader
- Linker
- Service
- Store
- validation / normalization
- shared model
- parser
- transport
- session/auth

→ 融入 `src/mmis_connector/<domain>/`。

#### C. Development / Diagnostic Tool

只負責：

- arguments
- session 建立
- 呼叫正式 component
- JSON stdout
- exit code
- 人工診斷流程

→ 留在 `tools/mmis_development/`。

#### D. Development-only implementation

只有 development tool 使用，Production 完全不需要，也沒有正式 reusable 價值。

→ 留在 `tools/mmis_development/`，或若已無任何參考／診斷價值則刪除。

---

## 6. 不要把「舊小程式」與「已演變成 Production component」混為一談

這是本專案曾經實際遇到的重要情況。

某個 module 最初可能是為了小功能建立，例如：

```text
query_unprocessed_fault_notices.py
```

但如果最後主程式已直接使用其中：

```text
UnprocessedFaultNoticeQuery
```

那它就不再只是「舊小程式」。

它已經成為 Production reusable component。

因此整理時不能因為它源自 development 階段就直接搬到 `tools/`。

判斷標準永遠是：

> 現在的 Production dependency，而不是歷史來源。

---

## 7. Production Source 的命名方式

Development Tool 可以使用操作式名稱：

```text
query_daily_inspection_work_order_by_number_and_link_fault_notice.py
```

Production implementation 則應依 domain responsibility 組織。

例如：

```text
src/mmis_connector/
├─ daily_inspection/
│  ├─ query.py
│  ├─ reader.py
│  └─ linker.py
├─ fault_notices/
│  └─ query.py
└─ auto_link/
   ├─ orchestrator.py
   └─ store.py
```

未來新增 domain 時，可依實際責任建立：

```text
src/mmis_connector/<domain>/
├─ query.py
├─ reader.py
├─ linker.py
├─ service.py
├─ store.py
└─ models.py
```

只建立實際需要的檔案，不要預先建立空架構。

---

## 8. 優先融入既有 Domain Package

新功能完成後，不要看到新功能就一定建立新的 package。

先檢查它是否屬於現有 domain。

例如：

- 故障通報相關 → `fault_notices/`
- 日檢工單相關 → `daily_inspection/`
- auto-link orchestration / state → `auto_link/`

如果新功能只是增加日檢工單的另一種正式能力，應優先融入：

```text
daily_inspection/
```

而不是建立：

```text
new_feature_xxx/
```

只有責任真的形成新的 domain 或 Production Application 時才建立新 package。

---

## 9. Mixed Module 的拆分原則

如果開發期間某個檔案同時包含：

```text
Reusable implementation
+ CLI arguments
+ JSON formatting
+ development-only helper
```

完成後應進行最小拆分：

```text
src/mmis_connector/<domain>/...
    └─ reusable implementation

tools/mmis_development/...
    └─ arguments / shell / diagnostic behavior
```

不要複製 implementation。

Production implementation 必須只有一份。

---

## 10. Production Application 的保留方式

主程式完成後，正式 application 應有清楚的 orchestrator／application boundary。

例如：

```text
src/mmis_connector/auto_link/orchestrator.py
```

Production CLI 應只負責：

```text
arguments
  ↓
建立 config/session
  ↓
呼叫 Production Application
  ↓
JSON stdout / exit code
```

不要把完整 business workflow 寫進 `cli.py`。

也不要讓 Production Application 呼叫 Development Tool。

---

## 11. Development Tools 是否保留

主程式完成後，逐一重新評估 development tools。

### 保留

若仍具有以下任一價值：

- debugging
- MMIS 行為確認
- controlled Live validation
- 人工單筆操作
- 未來新功能參考
- reusable component 單獨驗證

則留在：

```text
tools/mmis_development/
```

### 刪除

如果工具：

- 已完全沒有診斷價值
- 已被其他工具完整取代
- 沒有參考價值
- 未來不應再執行

才考慮刪除。

不要因為主程式完成就機械式刪除所有 development tools。

---

## 12. Public API 相容性

整理 `src/mmis_connector/` 時，檢查：

```text
src/mmis_connector/__init__.py
```

如果既有正式 public API 已支援：

```python
from mmis_connector import SomeProductionClass
```

在純 source organization refactor 中應盡量保持相容。

可以改 internal module path，但不要無意間破壞 package-level public API。

不要擅自擴張 public API。

---

## 13. 不要保留沒有必要的 Compatibility Shim

如果舊 internal module path 沒有明確 external compatibility requirement，完成 rename/move 後應移除舊檔案。

不要留下大量：

```python
from .new_path import *
```

形式的 forwarding shim。

否則 Production source tree 仍會保留開發時期的舊名稱，失去整理意義。

Package-level public API 與 internal module path 是兩件不同的事。

---

## 14. 行為凍結原則

「功能完成後整理」預設是 architecture / source organization refactor。

除非另有明確任務，禁止順便修改：

- Maximo HTTP payload
- event ordering
- app switching
- PAGESEQNUM
- UISESSIONID
- CSRF handling
- authentication
- retry policy
- parser semantics
- pagination
- table schema handling
- normalization
- validation
- mutation behavior
- mutation verification
- fail-closed behavior
- 已確認的 business rules

原則：

> Move code, do not redesign behavior.

> Preserve behavior first; improve source organization second.

---

## 15. 已驗證 Maximo 流程的特殊保護

如果某段 Query / Reader / Linker / mutation flow 已經：

- 通過 regression tests
- 使用 recorded evidence 驗證
- 或完成 controlled Live MMIS validation

不要因為「可以寫得更漂亮」而重新實作。

優先採用：

```text
move
rename
extract wrapper
update import
```

而不是重新設計 Maximo event sequence。

---

## 16. Architecture Tests 應保護的邊界

整理完成後，architecture tests 至少應保護：

### Production 不依賴 Development Tools

禁止：

```text
src/mmis_connector → tools/mmis_development
```

### Development Tools 可以重用 Production Components

允許：

```text
tools/mmis_development → mmis_connector
```

### Production 不使用 subprocess 串接自己的功能

正式 application 應直接使用 Python components。

### Production Source Inventory

`src/mmis_connector/` 中每個 module 都應能被分類為：

- Production Application
- Production reusable component
- shared infrastructure
- formal entry point

如果未來有人把歷史 script 放回 Production package，architecture test 應能偵測。

---

## 17. 整理完成後的驗證

整理前先記錄 baseline：

```powershell
python -m pytest
```

整理後至少執行：

```powershell
python -m pytest
python -m compileall -q src tests
python -m compileall -q tools/mmis_development
python -m pip check
git diff --check
```

另外依實際變更執行：

- package import smoke test
- Production CLI dispatch test
- Development Tool import test
- architecture tests
- public API tests

如果只是 rename / move / import refactor，原則上不應需要 Live MMIS mutation validation。

---

## 18. 建議使用 AST / Structural Comparison 保護純重構

如果是將已驗證 implementation 從舊 module move 到新的 domain package，可以比較移動前後：

- non-import AST
- function/class bodies
- public class names

目的是確認：

> 這次真的只是 source organization refactor，而不是偷偷改變 implementation。

如果可以做到，應將結果記錄在 verification report。

---

## 19. Codex 執行整理時的標準任務順序

Codex 在主程式完成後收到「依本指南整理」要求時，依序執行：

1. 閱讀 README、development workflow、production source inventory。
2. 執行修改前 test baseline。
3. 找出新主程式正式入口。
4. 建立完整 dependency graph。
5. 盤點本次開發期間新增的 tools / modules / helpers。
6. 將它們分類為 Production Application、Reusable Component、Infrastructure、Development Tool、Development-only implementation。
7. 找出可融入的既有 domain package。
8. 必要時建立新的 domain package，但不得預先過度設計。
9. 將 reusable implementation 實體 move / rename 到 Production domain。
10. 將 executable development-facing shell 留在 `tools/mmis_development/`。
11. 更新 imports、mocks、monkeypatch targets、tests、docs。
12. 檢查 `__init__.py` public API。
13. 移除沒有 compatibility requirement 的舊 internal module files。
14. 更新 architecture tests 與 production source inventory。
15. 執行完整 regression validation。
16. 比較修改前後行為與 test baseline。
17. 產生 verification report。

---

## 20. Codex 完成後必須回報

整理完成後至少提供：

### A. Before / After source tree

```text
Before:
src/mmis_connector/...

After:
src/mmis_connector/...
```

### B. Module mapping

| 開發／舊 module | 最終位置 | 分類 | Production 是否使用 | 是否保留 Development Tool |
|---|---|---|---|---|

### C. Dependency graph

列出新的 Production dependency closure。

### D. Development Tools

說明哪些保留、哪些刪除，以及理由。

### E. Behavior preservation

明確回答是否修改：

- Maximo HTTP/event behavior
- business logic
- parser behavior
- mutation behavior
- CLI contract
- JSON contract
- exit-code contract

### F. Public API

列出是否保持既有 package-level exports。

### G. Tests

回報：

- 修改前 pytest
- 修改後 pytest
- skipped 數量與原因
- compileall
- pip check
- git diff check
- architecture tests
- import smoke tests

### H. Live MMIS

說明是否執行 Live MMIS。

若只是純整理，預設不應執行會修改 MMIS 的 Live command。

---

## 21. 本專案已驗證過的整理案例

本指南來自既有 auto-link 功能的實際整理經驗。

開發期間曾存在操作式 Production module 名稱，最後確認其中的 Query / Reader / Linker 已成為正式主程式 dependency，因此沒有錯誤搬到 tools，而是重新依 domain responsibility 整理：

```text
query_unprocessed_fault_notices.py
→ fault_notices/query.py

query_daily_inspection_work_orders_by_vehicle_and_date.py
→ daily_inspection/query.py

query_fault_notices_linked_to_daily_inspection_work_order_by_number.py
→ daily_inspection/reader.py

link_fault_notice_to_daily_inspection_work_order_by_number.py
→ daily_inspection/linker.py

auto_link_unprocessed_fault_notices_to_daily_inspection_work_orders.py
→ auto_link/orchestrator.py

auto_link_store.py
→ auto_link/store.py
```

而 executable development-facing tools 則保留於：

```text
tools/mmis_development/
```

這個案例確立了本專案的長期原則：

> Development Tool 依「操作」命名；Production Code 依「責任／Domain」組織。

---

## 22. 最終判斷原則

每次整理時，遇到不知道某個檔案應放哪裡，依序問：

1. Production Application 現在是否直接或間接需要它？
2. 它是否是一個正式、可重用的 MMIS domain capability？
3. 它是否只是 arguments / JSON / debugging / manual execution shell？
4. 它是否只具有 development/reference 價值？
5. 它屬於哪個既有 domain？
6. 是否真的有必要建立新的 domain？
7. 移動它是否會迫使修改已驗證的 Maximo behavior？

最後遵守兩句話：

> 不要把「開發時建立的 module」等同於「development-only code」。

> 以完成後的 Production dependency 與 domain responsibility 決定最終位置。
