# 驗證報告

## 摘要

- 任務：依 domain responsibility 重整 Production modules
- 結果：通過
- 驗證者：Codex

六個 implementation 以實體 move 重整為三個 domain packages。class body、函式 body、
常數與所有非 import AST 均與修改前相同；未修改 Maximo protocol 或 auto-link business logic。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| 修改前 `python -m pytest` | 通過 | 129 passed、3 skipped |
| 針對性 pytest | 通過 | 58 tests；architecture、public API、CLI、tools、Store、Orchestrator |
| 修改後 `python -m pytest` | 通過 | 130 passed、3 skipped；新增 1 項 package public API 集合測試 |
| `python -m compileall -q src tests` | 通過 | 無輸出 |
| `python -m compileall -q tools/mmis_development` | 通過 | 無輸出 |
| `python -m pip check` | 通過 | No broken requirements found |
| package／CLI dispatch／development tools import smoke | 通過 | root exports、唯一 production command 與四個 tools 均可 import |
| 六個 moved modules non-import AST comparison | 通過 | 與修改前 HEAD 比對，僅 import nodes 不同 |
| old internal import path scan | 通過 | active source、tests、tools、README、docs、context maps 無殘留 |
| Production forbidden import／subprocess scan | 通過 | 無 `tools`、reference、examples、development 或 subprocess dependency |
| `git diff --check -- . ':(exclude)Prompt.md'` | 通過 | 本任務與其他專案 diff 無 whitespace error |
| `git diff --check` | 既有問題 | 僅使用者既有 `Prompt.md` 第 2、21 行 trailing whitespace；本任務未修改 |

3 個 skipped tests 是既有的選用 recorded-DOM tests，本次沒有新增 skip。

## UI 證據

不適用；本專案是 CLI，本次沒有 UI 變更。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 功能回歸、循環 import、API 漂移 | 無 | 針對性與完整測試、import smoke 均通過 |
| Production 反向依賴 tools／reference | 無 | recursive AST boundary scan 與 architecture test 通過 |
| Maximo／business behavior 意外修改 | 無 | 六個 moved modules 的非 import AST 完全一致 |
| 舊 internal module forwarding shim | 無 | 六個舊 `.py` 均已移除 |

核准建議：核准。

## MMIS 知識庫回寫

- section：`toolingNotes`
- id：`organize-production-mmis-services-by-domain-package`
- action：added
- deprecated：`name-mmis-feature-modules-by-action-and-domain`
- path：`C:\Users\NMMIS\.codex\skills\mmis-dev-knowledge\references\knowledge-base.json`

## 殘留風險

- Repository 外若直接 import 從未承諾的舊 internal module path，需要遷移；root
  `mmis_connector` package-level API、Production CLI 與 development tool commands 均保持。
- 原始 `git diff --check` 仍會回報使用者既有 `Prompt.md` 兩行尾端空白。
- 本次不需要且未執行 Live MMIS 驗證；完整行為由離線 regression 保護。
