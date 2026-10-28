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

## 第十二階段：依結案狀態檢查填寫離線 Excel 備註（2026-10-21）

- 依使用者提供的 `備註規則.csv` 四筆規則，以六個欄位的完整 `NULL/0/1` 組合精確比對。
- 四筆組合依序為 `(NULL,1,0,0,0,0)` 對應「段修工單未處理完成」、`(NULL,1,0,1,0,0)` 對應「等候段修工單簽核中」、`(NULL,1,1,0,0,0)` 對應「可結案」、`(0,0,0,0,0,0)` 對應「未處理」。欄位順序沿用現有六個結案狀態檢查欄位。
- 命中時 Excel 備註填入規則文字，未命中時保留 SQLite 原備註。資料庫維持唯讀；不連線 MMIS、不依賴執行時可存取個人 Downloads 目錄、不改原同步匯出。
- 六個狀態欄只接受 `NULL`、`0`、`1`；無效值導致匯出失敗。驗收讀回四筆匹配、近似但不匹配的組合、既有備註及原資料庫內容。

## 第十三階段：同步指令改用獨立匯出器（2026-10-21）

- 使用者要求 `auto_process_unclosed_ab_fault_notices --export-xlsx` 在同步完整成功後，呼叫 `export_unclosed_ab_fault_notices_from_db` 的匯出流程。Excel 改用獨立指令目前的九欄、排序、欄寬、備註規則與輸出檔名。此項取代前述保留 15 欄同步匯出格式的約束。
- 移除同步指令直接組裝 Excel 的程式。同步失敗或部分成功時不匯出；匯出失敗時保留已提交的 SQLite 並回報失敗。從同步指令匯出時須核對資料庫筆數與本次同步筆數。
- `export_unclosed_ab_fault_notices_from_db` 可獨立從既有 SQLite 匯出，不執行 MMIS 查詢或同步。
- 非目標：變更 SQLite schema、MMIS 查詢、故障分析寫入及獨立指令的輸出格式。

## 第十四階段：同步時重置故障分析完成備註（2026-10-21）

- 使用者要求每次全量同步時清除舊快照的「填寫故障分析完成」。此項取代第六階段在下次同步時保留該備註的約束。
- 新快照的 `備註` 預設為 `NULL`；不因舊快照相同通報號而回填。只有本次確認 MMIS 故障分析寫入成功後，才重新標記。
- 已在 MMIS 完成故障分析的通報不再執行 AI 寫入，且新快照的 `備註` 保持 `NULL`。快照交易失敗時回滾；快照提交後的明細或 MMIS 寫入失敗不回滾快照。
- 非目標：更改 MMIS 結案狀態、等候結案資料庫、SQLite schema 或 Excel 格式。

## 第十五階段：待簽核且故障分析未完成時標記未處理（2026-10-22）

- Excel 匯出時，六個結案狀態檢查值依原欄位順序精確等於 `(NULL,0,0,1,0,0)`，備註填「未處理」。此規則與既有四筆規則共用同一個查表邏輯。
- 其他狀態組合維持原規則；未命中時保留 SQLite 原備註。只改 Excel 內容，不寫回 SQLite，不改 MMIS 查詢或同步流程。
- 驗收以暫存 SQLite 匯出並讀回 XLSX，確認命中組合覆蓋原備註、相近組合保留原備註，且資料庫未變。
- 實際同步若發現故障分析未完成，會再次檢查資料充分性；當結果為 `false` 時，SQLite 的第一欄為 `0`。因此 `(0,0,0,1,0,0)` 也須填「未處理」，與上述 `NULL` 組合共用規則表。

## 第十六階段：段修工單結案但故障分析未完成時標記未處理（2026-10-28）

- Excel 匯出時，六個結案狀態檢查值依原欄位順序精確等於 `(0,0,1,0,0,0)`，備註填「未處理（段修工單結案）」。
- 此狀態與待簽核但段修未結案的 `(0,0,0,1,0,0)` 分開處理；其他狀態維持原規則，未命中時保留 SQLite 原備註。
- 只改 Excel 匯出內容，不寫回 SQLite，不改 MMIS 查詢或同步流程。
- 驗收以暫存 SQLite 匯出並讀回 XLSX，確認命中組合、相鄰狀態組合及原備註行為，且資料庫未變。

## 第十七階段：含 ATP 故障分析未完成時標記未處理（2026-10-28）

- `auto_process_unclosed_ab_fault_notices --export-xlsx` 使用的離線匯出器，在六個結案狀態檢查值依原欄位順序精確等於 `(1,1,0,1,0,1)` 時，將 Excel「備註」填為「未處理（含ATP故障分析）」。
- 其他組合沿用既有精確對照規則；未命中時保留 SQLite 原備註。不寫回 SQLite，不變更 MMIS 查詢或同步流程。
- 驗收以暫存 SQLite 匯出並讀回 XLSX，確認指定組合、相近組合、既有備註和資料庫未變。

## 第十八階段：自動填寫 ATP 故障分析（2026-10-28）

- 狀態：使用者已於本次對話核准實作。風險等級：高，涉及 MMIS 遠端寫入。
- 當通報符合現有一般故障分析自動填寫條件，且 `ATP Fault Analysis Incomplete = true` 時，同一次完整通報 AI 查詢須取得一般故障分析三欄。ATP 三欄全空時也須取得合法的 ATP 分類三欄；此時 ATP 建議缺失或分類驗證失敗，不得送出任何 MMIS 寫入。ATP 已部分填寫時不要求 AI 建議，僅執行原有一般分析寫入。
- ATP 寫入只支援錄製證實的三欄全空狀態。若寫入時 ATP 未勾選、任一欄已有文字，或 MMIS 已變更，應拒絕 ATP 寫入，不覆蓋既有分類；已確認為部分填寫時，一般故障分析仍依原規則執行，並回報 ATP 尚未填寫。
- 同時需寫兩者時，先填寫並儲存 ATP 分析，再填寫一般故障分析。每項都須確認儲存成功訊息並獨立回讀核對；結果不明時不自動重送。
- 每項 MMIS 寫入與回讀確認後，才在本次 SQLite 快照的 `備註` 追加相應文字 `已填寫ATP故障分析`、`已填寫故障分析`。保留當次既有文字，同一文字不重複追加；只成功一項時只註記該項。下次全量同步仍依第十四階段清空舊備註。
- `ATP Fault Analysis Incomplete = false` 時維持一般故障分析原流程。Excel 備註沿用 SQLite 值與既有離線規則，不更改格式。
- 驗證使用 2026-10-28 ATP 填寫錄製的三次 setvalue 與儲存事件、暫存 SQLite 與 mock HTTP 測試；不以測試執行正式 MMIS 寫入。

## 第十九階段：將備註規則寫入 SQLite（2026-10-28）

- 使用者已明確要求實作。此階段取代第十四階段及第十八階段「下次全量同步清空舊備註」的要求，也取代第十二、十五至十七階段只在 Excel 產生規則備註的要求。
- 同步時按六個狀態欄的完整 `NULL/0/1` 組合，將既有八筆備註規則的結果寫入 `unclosed_ab_fault_notices.db` 的「備註」欄。預設指令與加上 `--export-xlsx` 的指令都要完成此寫入。
- 同一通報既有的「已填寫ATP故障分析」及「已填寫故障分析」標記，在全量同步及規則重算後仍須保留。規則備註不得阻止符合條件的 AI 故障分析流程。
- Excel 匯出只讀取資料庫備註，不再依狀態欄產生或覆蓋備註。既有九欄、排序、欄寬、列高、字型及檔名規則維持一致。
- 不變更 SQLite schema 或 MMIS 查詢及寫入契約。以暫存資料庫測試預設同步、加旗標匯出、舊標記保留、規則精確比對、匯出唯讀及失敗時的交易行為；不執行正式 MMIS 寫入。
