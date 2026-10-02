# 功能規格書

## Metadata

- 功能：依通報號整合故障通報、段修工單與故障分析查詢
- 負責人：Codex
- 狀態：使用者於 2026-10-02 核准，已實作
- 風險等級：高（重用既有認證與內部網路唯讀查詢）

## 問題

同一筆故障通報的 ATP 標記、兩類工單及分析資料分散在四個命令中。使用者需要一次輸入通報號，取得可直接處理的單一 JSON。

## 使用者

使用命令列查詢已授權 MMIS 故障通報的內部使用者。

## 目標

- 以一個通報號查得唯一且完全相符的故障通報。
- 在一次登入、同一個 MMIS session 中讀取 ATP 勾選狀態、所有段檢修工單、CA 查修工單、故障分析五欄及條件式 ATP 分析三欄。
- stdout 只輸出一個 JSON；不產生查詢結果檔。

## 非目標

- 不修改 MMIS 故障通報、工單或勾稽關係。
- 不改動四個既有獨立查詢命令的公開輸出契約。
- 不加入正式 `mmis_connector` CLI；新入口放在 `tools/mmis_development`。
- 不保存帳密、session、HAR 或查詢結果。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 整合查詢 | 身為內部使用者，我想只輸入一次通報號，以便一次取得完整資料 | 單一命令輸出下列完整 JSON 契約；所有資料對應同一個精確通報號 |
| 條件式 ATP 分析 | 身為內部使用者，我想區分非 ATP 通報與 ATP 分析空欄，以便正確判讀 | 未勾選輸出 `false` 與 `null`；已勾選輸出 `true` 與三欄物件，空欄保留空字串 |

## 使用者旅程

```text
輸入通報號 → 驗證格式 → 登入並找到唯一明細 → 讀 ATP 勾選狀態
→ 讀故障追蹤中的兩張完整工單表 → 讀故障分析五欄
→ 若 ATP 已勾選，讀故障分析-ATP 三欄 → 印出單一 JSON
```

## 功能需求

- WHEN 執行整合查詢，THE SYSTEM SHALL 在 JSON 第一層最前面依序輸出通報號、事故等級、狀態、發生日期、車次、車組/車號；不得新增 `查詢故障通報基本資料` 包裝項，也不得重複輸出通報號。其後保留原有 ATP 標記、工單與分析項目的順序與內容；事故現象只在故障分析內出現。
- WHEN 明細日期 input 的 value 為空，THE SYSTEM SHALL 使用畫面顯示的 title 日期；同名欄位若有多個且值不一致，THE SYSTEM SHALL 失敗而非任選一筆。

- WHEN 使用者提供一個符合 `7 位數字-2 位數字` 的通報號，THE SYSTEM SHALL 在登入前完成格式驗證。
- WHEN 查詢結果不存在、不唯一或與輸入不完全相符，THE SYSTEM SHALL 輸出 JSON 錯誤並以非零退出碼結束，不輸出部分成功資料。
- WHEN 通報明細可讀取，THE SYSTEM SHALL 從「故障通報立案」的 ATP 故障勾選狀態輸出布林值；標記結構不明時應失敗。
- WHEN 開啟「故障追蹤」，THE SYSTEM SHALL 讀取「檢視所有段檢修工單」及「查修工單」完整分頁，分別輸出為頂層 `段修工單` 與 `CA查修工單` 陣列，沿用既有欄位、CA 篩選、工作單去重與原順序；空表輸出空陣列。
- WHEN 開啟「故障分析」，THE SYSTEM SHALL 讀取事故現象、處理概況、故障原因、處理情形及改善對策，保留合法空字串。
- WHEN ATP 故障已勾選，THE SYSTEM SHALL 再開啟「故障分析-ATP」讀取故障要因、故障因子及故障項目；未勾選時不開啟此子頁籤。
- WHEN 分頁、欄位或頁籤結構缺失或矛盾，THE SYSTEM SHALL 輸出 JSON 錯誤並以非零退出碼結束。

## 畫面

無新 UI；僅操作既有 MMIS 頁籤並產出命令列 JSON。

## 資料與 API

- 輸入：`python -m tools.mmis_development.query_fault_notice_full_detail <通報號>`（建議命名，待核准）。
- 成功輸出範例（欄位值僅示意）：

```json
{
  "通報號": "1150210-36",
  "事故等級": "",
  "狀態": "",
  "發生日期": "",
  "車次": "",
  "車組/車號": "",
  "是ATP故障": true,
  "段修工單": [],
  "CA查修工單": [],
  "故障分析": {
    "事故現象": "",
    "處理概況": "",
    "故障原因": "",
    "處理情形": "",
    "改善對策": ""
  },
  "ATP故障分析": {
    "故障要因": "",
    "故障因子": "",
    "故障項目": ""
  }
}
```

- `段修工單` 每筆保留「檢視所有段檢修工單」既有七欄；`CA查修工單` 每筆保留「查修工單」既有十欄。兩張表可能包含同一工作單，各自保留，不跨表合併不同欄位。
- ATP 未勾選時，`是ATP故障` 為 `false`，`ATP故障分析` 為 `null`。
- 錯誤沿用 `tools.mmis_development._support.run_json_tool` 的 `success: false`、`error`、`message` JSON 契約與非零退出碼。
- 既有認證：`.env` → `MMISSession` → `MaximoEventClient`；只發送導覽、查詢與分頁事件。

## 安全性與隱私

- 只使用已授權的 MMIS 帳號及既有同源 HTTPS/session 機制；不輸出憑證、cookie、token 或原始 HTML。
- 故障分析與工單可能含業務敏感文字；查詢結果僅輸出至本次命令的 stdout，不落盤。
- 不使用瀏覽器或 subprocess 呼叫四個命令；重用 domain reader 與解析器。

## 驗收標準

- 一次登入、一個 session，完整輸出上述十一個頂層鍵；六個基本欄位置頂、通報號只出現一次，兩類工單分別為獨立陣列。
- ATP 已勾選及未勾選兩條路徑均有明確且穩定的 JSON。
- 兩張工單表的零筆、多筆、跨頁及去重行為與既有獨立查詢一致。
- 通報格式錯誤、查無、非唯一、頁面結構漂移均產生 JSON 錯誤和非零退出碼。
- 四個既有命令與測試保持可用。

## 驗證計畫

- 單元／離線整合測試：已勾選、未勾選、空表、跨頁、欄位空值及錯誤路徑；確認登入一次且不發送修改事件。
- 回歸：`python -m pytest`、`python -m compileall src tools`、`git diff --check`。
- 唯讀 live 驗證：在可用且已授權的 MMIS 環境下，以指定通報號比對現有命令輸出；若環境不可用，明列此限制。
- UI 截圖：不適用，沒有 UI 變更。

## 情境包

- 任務：整合四個故障通報 development tool 的查詢結果。
- 相關檔案：`src/mmis_connector/fault_notices/{reader,atp_reader,linked_work_orders,repair_work_orders}.py`、`tools/mmis_development/_support.py` 與四個既有入口。
- 既有模式：精確通報號查詢、語意化頁籤與欄位解析、同一 session 的 Maximo event、stdout JSON。
- 假設：`段修工單` 與 `CA查修工單` 為兩個頂層陣列；ATP 未勾選時分析值為 `null`。
- 已確認事項：使用者要求兩類工單分開成兩個頂層 JSON 項目；命令名稱依規格建議採用。
- 預計允許變更：新整合 domain reader、新 development tool、相關測試及核准後的任務／驗證產出物；必要時小幅重構既有 reader 以共用已開啟的頁面與分頁讀取。
- 不得觸碰：使用者已修改的 `Prompt.md`、既有獨立命令的公開契約、認證與遠端寫入流程。
- 驗證指令：`python -m pytest`、`python -m compileall src tools`、`git diff --check`。
- 風險等級：高（既有認證及內部網路邊界，唯讀）。
- 情境預算備註：已讀 project/architecture/search maps、四個入口及四個 domain reader、相關既有規格與知識庫相關規則；未讀整個 repository 或敏感錄製資料。
