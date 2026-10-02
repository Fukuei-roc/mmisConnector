# AI-Ready 任務卡

## Metadata

- 任務：建立 HTTP-only ATP 故障分析查詢工具
- 上層 Epic／User Story：MMIS HTTP ATP故障分析查詢／依通報號讀取 ATP 故障分析
- 規格：`ai/artifacts/MMIS HTTP ATP故障分析查詢/feature-spec.md`
- 人工核准：使用者於 2026-10-02 明確要求開發
- 狀態：實作與驗證完成，待人工驗收
- 前置任務：既有 HTTP 登入、故障通報精確詳情查詢已完成
- 風險等級：高（認證與內網唯讀查詢）

## 情境包與範圍

- 相關檔案：`fault_notices/reader.py`、`parser.py`、`events.py`、`tools/mmis_development/`、2026-10-02 ATP 錄製 HAR 與 DOM。
- 既有模式：薄 wrapper → domain reader → 同一 HTTP session → 動態 Maximo event target → 依可見 label/for 擷取。
- 錄製證據：詳情回應含 ATP 勾選圖示；點「故障分析」與「故障分析-ATP」各為一次 click event；最終 DOM 目標三欄均為 input。
- 假設：錄製中的可見標籤仍有效；未勾選的圖示以明確狀態文字或 `cb_unchecked` 圖名表示。
- 未知：未來 MMIS DOM 漂移；遇到不一致狀態應拒絕解析。
- 允許變更：相鄰 parser、新 ATP reader、薄 wrapper、對應 tests、開發 README、專案地圖與本 Epic 文件。
- 不得觸碰：`.env`、外部錄製、遠端資料、既有 `Prompt.md` 修改、瀏覽器程式。
- 情境預算：已讀流程、DoR/DoD、地圖、相鄰 reader/parser/tool、錄製 README/summary、關鍵 HAR events 及最終 DOM；跳過靜態資源與敏感 headers/cookies。

## 驗收與驗證契約

- 精確命中唯一通報；ATP 未勾選時不點頁簽；已勾選時兩個頁簽依序點擊。
- 只將三個指定欄位以 label/for 關聯讀值；空值為 `""`；缺欄失敗；不輸出其他 ATP 欄位。
- 執行針對性與完整 pytest、compileall、diff check，以及指定通報 `1150210-36` 的唯讀 live 查詢。
- 無資料模型變更或遷移；回滾為移除新 reader/wrapper/test 並還原 parser、README、地圖。

## 完成證據

參見 `verification/MMIS-026.md`。
