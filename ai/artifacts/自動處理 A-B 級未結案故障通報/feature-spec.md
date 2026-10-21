# 功能規格書

## Metadata

- 功能：Auto Process Unclosed AB Fault Notices，第一階段
- 負責人：專案使用者
- 狀態：人工已核准（2026-10-19 任務指示）
- 風險等級：高（本機資料庫全量覆蓋）

## 問題

需要建立可重跑的 A/B 級未結案故障通報本機 snapshot，供後續階段使用。

## 使用者

執行 Development Tool 的 MMIS Connector 使用者。

## 目標

- 重用既有未結案查詢，將八個基本欄位寫入固定 SQLite 資料表。
- 成功時全量替換；查詢、驗證或寫入失敗時保留舊資料。

## 非目標

- 完整明細、工單、AI、六個結案狀態檢查、備註填寫、歷史保存、MMIS mutation、Production CLI。

## 使用者故事（User Stories）

| 故事 | 身為／我想要／以便 | 驗收標準 |
|---|---|---|
| 建立 A/B 級未結案通報 snapshot | 身為開發工具使用者，我想取得本次完整查詢快照，以便後續逐階段處理 | 15 欄 schema、8 欄來源資料、7 欄 NULL；成功全量覆蓋，失敗保留舊資料 |

## 使用者旅程

```text
執行零參數 Python module → 完整查詢及驗證 → SQLite transaction 全量覆蓋 → stdout JSON summary
```

## 功能需求

- WHEN 既有 `UnclosedFaultNoticeQuery` 回傳成功、正確 query 與 filters 且 count 等於 records 長度，THE SYSTEM SHALL 驗證所有基本欄位並儲存。
- WHEN 有缺欄、無通報號、重複號、非 A/B 等級或型別錯誤，THE SYSTEM SHALL 拒絕整批。
- WHEN 結果成功且為空，THE SYSTEM SHALL 清空既有列。
- WHEN 查詢或 transaction 失敗，THE SYSTEM SHALL 保留舊列。

## 畫面

無 UI。

## 資料與 API

- 輸入：既有 Query 的 `success/query_name/filters/count/records` dict。
- 輸出：`data/unclosed_ab_fault_notices.db` 與 stdout JSON summary。
- 驗證：query 身分、筆數、八欄、A/B、通報號唯一與 SQLite schema。
- 錯誤：exit code 1；JSON 說明原因、transaction、rollback 與舊資料狀態。

## 安全性與隱私

- 身分驗證：沿用既有 `MMISSession`；不新增憑證處理。
- 權限：只使用唯讀 MMIS 查詢。
- 敏感資料：JSON summary 不包含逐筆通報或認證資訊。
- 濫用情境：不完整查詢或錯誤 schema 不得清空既有資料。

## 驗收標準

- 15 欄依指定順序；`通報號` 為 `TEXT PRIMARY KEY NOT NULL`。
- ATP 布林依 true/false/null 對應 1/0/NULL，七個預留欄位永遠 NULL。
- 舊列、舊預留欄位內容在下一次成功同步後消失。
- 資料庫相對專案根目錄定位；不修改其他 data 檔案或 Production CLI。

## 驗證計畫

- 單元測試：查詢結果驗證、schema、NULL、全量覆蓋與錯誤路徑。
- 整合測試：mock Query + 暫存 SQLite；既有查詢與 Development Tool 回歸。
- E2E：本階段不執行 Live MMIS。
- 視覺：不適用。
- 手動：檢查 diff、README 與指令輸出。

## 第二階段：只查詢首筆完整通報（2026-10-20）

- 使用者要求保留既有 15 欄 snapshot，成功儲存後只查詢本次來源結果第一筆通報，不處理後續筆數。
- 直接呼叫 `query_fault_notice_full_detail.execute()`；核對通報號及六欄布林／NULL 型別，以單筆 SQLite transaction 回填；備註及其他通報的檢查欄位維持 `NULL`。
- 預設模式沿用完整通報查詢的非 AI 契約：第一欄 `Sufficient Data for Fault Analysis` 為 `NULL`，其餘五欄為布林值。明確加 `--check-analysis-readiness` 才呼叫付費 OpenAI 並要求第一欄為布林值；不執行 `--ai-analysis`。
- 明細查詢或更新失敗時，已成功建立的完整 snapshot 保留，錯誤 JSON 標示 snapshot 與單筆更新階段；不回滾整個 snapshot。
- 此增量不改變第一階段已完成任務卡 MMIS-045 的歷史驗證紀錄。

## 第三階段：逐筆查詢並保存等候結案 A 級通報（2026-10-20）

- 英文名稱：A-Level Fault Notices Awaiting Closure；獨立資料庫 `data/a_level_fault_notices_awaiting_closure.db`，資料表 `a_level_fault_notices_awaiting_closure`。
- 等候結案庫只有 `通報號`（TEXT PRIMARY KEY NOT NULL）與 `新增日期`（TEXT NOT NULL）；新增日期為當下台北時間的 ISO 日期時間，不因重跑改寫。
- 本次 MMIS 清單仍須完整查詢與驗證。讀取既有等候結案通報號後，從主 snapshot 排除；餘下全部通報依來源順序逐筆呼叫完整通報 Python 查詢。
- A 級且五個指定欄位依序為 true、true、false、false、false 時，將通報號與新增日期寫入等候結案庫，並從主資料表移除；`Sufficient Data for Fault Analysis` 不參與判斷。B 級或未符合者留在主資料表。
- 兩庫搬移使用 SQLite attached database transaction，確保單筆插入與刪除一起 commit 或 rollback。明細失敗時保留已完成 snapshot 和先前成功處理的結果，錯誤摘要標示部分進度。
- 預設模式不呼叫 AI；明確加入 `--check-analysis-readiness` 才對待處理通報逐筆啟用付費 AI。

## 第四階段：條件式資料充分性檢查（2026-10-20）

- 預設執行時先查每筆未列入等候結案庫的通報，保存五項非 AI 檢查值。
- 只有首輪 `Fault Analysis Completed` 為 `false` 時，才以相同通報號再呼叫完整明細查詢的 `--check-analysis-readiness`，取得 `Sufficient Data for Fault Analysis` 的 boolean 並只回填此欄。
- `Fault Analysis Completed` 為 `true` 時第一欄保留 `NULL`，不呼叫 AI。舊的明確 `--check-analysis-readiness` 旗標仍對每筆通報執行既有行為。
- 第二次查詢須再次驗證通報號及六欄型別；查詢或寫入失敗即回報失敗，保留首輪已寫入的五項值。等候結案庫仍不重置，也不變更 A 級搬移條件。
- 預設執行可能呼叫付費 OpenAI API，需 `OPENAI_API_KEY`；不呼叫 `--ai-analysis`，不修改 MMIS。
- 若相關工單查詢失敗使 AI 證據不完整，資料充分性維持 `NULL`，不推測 true/false；跳過該筆 AI 判斷並繼續後續通報，最後以 `partial_success`、未完成清單與非零 exit code 回報。確定性的證據不完整錯誤不重試整筆完整明細。

## 第五階段：同步完成後匯出 XLSX（2026-10-20）

- 原指令保持既有同步與 JSON 行為、不產生 XLSX。新增 `--export-xlsx` 只在完整同步成功後，從本次已提交的 `data/unclosed_ab_fault_notices.db` 唯讀匯出 15 欄。
- `partial_success`、查詢失敗或 SQLite 寫入失敗均不匯出。匯出失敗時保留已提交 SQLite，JSON 明確區分同步成功與匯出失敗，非零 exit code。
- 輸出資料夾由 `.env` 的 `UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR` 設定；不存在時報錯，不自行建立 OneDrive 路徑。
- 工作表 `AB級未處理故障通報`，微軟正黑體 12 pt；標題粗體置中，資料靠左；自動估算欄寬、長文字換行與列高。NULL 為空白，七個布林欄位依 1/0 輸出 TRUE/FALSE；所有字串以文字型別避免公式注入。
- 台北日期檔名 `AB級未處理故障通報_程式產生MMDD.xlsx`；排他建立同名序號檔，避免覆蓋與併發競爭。離線測試使用暫存資料庫與 XLSX，不連線 Live MMIS。

## 第六階段：同步成功後填寫故障分析（2026-10-21）

- 使用者明確授權 MMIS 寫入。完整同步成功後，從主 SQLite 挑選 `Sufficient Data for Fault Analysis = 1`、`Fault Analysis Completed = 0` 的通報號。
- 每筆重用完整通報查詢的 `--ai-analysis`，將其「故障原因」、「處理情形」、「改善對策」寫入 MMIS「故障分析」頁簽，觸發「儲存故障通報管理」。
- 保存後重新查詢並核對三欄；確認成功才在主 SQLite 的「備註」寫入「填寫故障分析完成」。不修改 `Fault Analysis Completed`。
- MMIS 欄位已有非空文字時予以保留，只以 AI 內容補空欄。
- 已標記成功的備註在下一次同步時保留；若最新 MMIS 檢查仍顯示分析未完成，清除舊備註再處理。
- 不完整同步、AI 輸出無效、通報號不符或遠端保存結果不明時不得寫備註；遠端保存不自動重送。
- 無符合資料時不執行 AI 或 MMIS 寫入；既有 schema 及其他匯出行為維持原狀。

## 第七階段：從既有 SQLite 離線匯出 XLSX（2026-10-21）

- 新增獨立開發指令，從現有 `data/unclosed_ab_fault_notices.db` 唯讀匯出 Excel，不查詢 MMIS、不重建資料庫，也不修改原同步指令。
- 重用第五階段的 15 欄順序、布林值轉換、格式、輸出路徑與檔名規則。輸出使用相同的 `UNCLOSED_AB_FAULT_NOTICES_XLSX_DIR` 設定。
- 資料庫不存在、schema 不符或輸出目錄無效時回報 JSON 錯誤，不建立資料庫或不完整的 Excel。成功時回報匯出路徑與筆數。
- 驗收以暫存資料庫測試與現有資料庫實際匯出證明，並核對資料庫內容未變。

## 第八階段：調整離線匯出 Excel 內容（2026-10-21）

- 離線匯出保留八個基本欄位與 `備註`，不輸出六個英文結案狀態檢查欄位。資料庫 schema 仍維持原本 15 欄。
- 離線匯出工作表的表頭與資料列均固定 15.5 pt，所有儲存格垂直靠上，既有水平對齊維持原設定。
- 原 `auto_process_unclosed_ab_fault_notices --export-xlsx` 的 15 欄、列高及對齊維持原行為。
- 以 openpyxl 讀回兩種工作簿核對欄位、列高及對齊；不查詢 MMIS，不改寫 SQLite。

## 第九階段：指定離線匯出欄寬與排序（2026-10-21）

- 離線 Excel 九欄依序設定欄寬：車次 6.5、車組/車號 11.8、發生日期 14.5、事故等級 10.6、ATP故障 10.6、故障現象 70、狀態 10.6、通報號 14.9、備註 40。
- 全部資料依「事故等級」、「發生日期」、「車組/車號」逐級遞增排序。相同排序鍵維持 SQLite 原列順序，空值排在非空值後。
- 讀取並驗證完整 15 欄 schema 後排序和投影；SQLite 內容及原同步指令的匯出格式不變。
- 以刻意打亂順序的暫存資料庫測試排序優先序，並從 XLSX 讀回九個指定欄寬；用現有資料庫實際匯出核對。

## 第十階段：依結案狀態填色並追加備註（2026-10-21）

- 離線 Excel 仍只輸出九欄，但依原 SQLite 的六個狀態欄判斷「通報號」儲存格的填滿色。
- `Fault Analysis Completed = 1`、`Depot Maintenance Work Orders Pending Approval = 1`、`CA Repair Work Orders Not Closed = 0`、`ATP Fault Analysis Incomplete = 0` 時填淺綠 `#92D050`，並在 Excel「備註」欄加入「段檢修工單等候簽核」。已有文字時先保留原文，再換行加入。
- `Sufficient Data for Fault Analysis = 1`、`Fault Analysis Completed = 0`，且後三個工單與 ATP 條件分別為 `1/0/0` 時填橄欖綠 `#C4D79B`，不新增備註。
- `Sufficient Data for Fault Analysis = 0` 時填黃 `#FFFF00`，不新增備註。規則按列出順序判定；第一項與第三項同時成立時採第一項。
- 空值不視為 true 或 false。只修改記憶體中的工作簿，SQLite、MMIS 與原同步匯出保持原狀。
- 用暫存 SQLite 覆蓋三種顏色、條件不成立、重疊優先序、既有備註、公式安全和排序後的列對應；實際匯出現有資料庫並讀回。

## 第十一階段：移除離線匯出的狀態填色（2026-10-21）

- 使用者撤回第十階段的三條填色規則，包含第一條附帶的「段檢修工單等候簽核」備註追加。
- 離線 Excel 的所有儲存格均不因結案狀態填滿顏色；`備註` 只呈現 SQLite 原值，不產生額外文字。
- 保留九欄、15.5 pt 列高、垂直靠上、固定欄寬、三級遞增排序，以及原同步匯出行為。
- 刪除只為這三條規則存在的逐列裝飾程式與介面；用包含原三種條件的暫存 SQLite 驗證沒有填色或追加備註，並以現有資料庫實際匯出核對。
