# 驗證報告

## 摘要

- 任務：MMIS-028，在整合查詢 JSON 置頂加入故障通報基本資料
- 結果：通過，使用者已確認測試正常
- 驗證者：Codex，2026-10-02

## 行為與變更

- `src/mmis_connector/parser.py` 新增 `parse_fault_notice_basic_info`：依 label/for 讀六欄；日期優先使用 input value，其次顯示用 title，再按台北時區讀 dojovalue；同名欄位值不一致、缺欄或通報號不符則失敗。
- `src/mmis_connector/fault_notices/full_detail.py` 從已取得的通報明細讀取基本資料，將六欄直接展開為 JSON 前六個頂層項目；通報號只輸出一次，後續 ATP 標記、工單與分析的名稱、順序及內容不變。
- `tests/test_fault_notice_full_detail.py` 驗證前六個頂層欄位及順序、沒有基本資料包裝項或重複通報號、事故現象不重複、日期、重複標籤、缺欄及錄製 DOM。
- 更新本 Epic 規格、架構筆記、任務卡與專案搜尋地圖；原有 `Prompt.md` 修改未動。

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest tests/test_fault_notice_full_detail.py -q` | 通過 | 合成 DOM 與本機錄製 DOM 解析成功 |
| `python -m pytest` | 通過 | 170 passed、10 skipped，1.69s；跳過的 10 項為其他功能所需的本機錄製 DOM 不可用 |
| `python -m compileall -q src tools` | 通過 | 無輸出 |
| `git diff --check` | 通過 | 無空白錯誤；Git 有 Windows 行尾轉換提示 |
| `python -m tools.mmis_development.query_fault_notice_full_detail 1150910-14` | 通過 | 唯讀 live；前六個頂層鍵及值與錄製資料一致，無包裝項及重複通報號；後續五項均在；段修 3 筆、CA 0 筆 |
| `python -m tools.mmis_development.query_fault_notice_full_detail 1150210-36` | 通過 | 唯讀 live；基本資料六欄存在，ATP 已勾選且原三欄 ATP 分析存在 |

## UI 證據

無 UI 變更，螢幕截圖不適用。錄製檔僅在本機讀取，未複製到 repository。

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 車次與車組/車號在錄製明細中各有兩個同名標籤 | 中 | 已要求值一致；衝突時 JSON 錯誤停止 |
| 發生日期 input value 為空，顯示日期位於 title | 中 | 已優先讀 title，並以 dojovalue 作為無 title 時的備援 |

## 安全性與可維護性審查

- 認證與網路：只讀取既有通報明細回應，不新增登入、HTTP event 或寫入路徑。
- 輸入與資料：沿用精確通報號驗證，基本資料再次比對通報號；缺欄或值矛盾時不輸出部分成功資料。
- 隱私：不保存或輸出錄製 HAR、cookie、token、原始 HTML；僅輸出要求的業務欄位。
- 架構：解析器負責 DOM，domain reader 負責輸出順序；既有四個獨立查詢命令契約不變。
- 核准建議：可交由使用者人工驗收。

## 殘留風險

- MMIS 若改動欄位標籤或 label/for 關係，解析會以 JSON 錯誤停止；需用新錄製資料更新解析規則。
- 10 項條件式錄製 DOM 測試因對應本機檔案不可用而跳過，與本次六欄錄製測試無關。

## 人工驗收

- 使用者於本次對話確認「測試正常」。

## 後續任務

- 無。
