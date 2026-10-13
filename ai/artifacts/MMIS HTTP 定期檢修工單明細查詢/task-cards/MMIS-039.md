# AI-Ready 任務卡

## Metadata

- 任務：查詢定期檢修工單明細中的非空備註
- 上層規格：`ai/artifacts/MMIS HTTP 定期檢修工單明細查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 定期檢修工單明細查詢
- 上層 User Story：查詢定期檢修記錄
- 分軌：後端
- 前置任務：無
- 狀態：完成；使用者本次需求授權
- 風險等級：中；既有登入與唯讀 HTTPS 查詢
- Agent owner：Codex
- 人工核准者：專案使用者（本次明確需求）

## 目標與情境包

- 目標：新增單一工作單號查詢工具，JSON 的「檢修記錄」只含備註非空的四欄資料。
- 相關檔案：`tools/mmis_development/`、`src/mmis_connector/{events,parser,daily_inspection,periodic_inspection}/`、指定 Recorder DOM/HAR。
- 既有模式：`MMISSession`、`MaximoEventClient`、語意表頭定位、分頁完整性檢查、薄 development wrapper。
- 假設：沿用既有 `count`/`records` JSON 契約；全部空白為成功的空清單。
- 未知事項：錄製只有單頁 58 筆；跨頁以既有 Maximo 分頁事件與合成案例驗證。
- 允許變更：新 domain reader/tool/test、tools README、架構清單、專案地圖與搜尋指南及本 Epic 治理產出物。
- 不得觸碰：認證設定、正式 CLI、其他工單查詢流程及外部錄製資料。
- 情境預算：閱讀專案地圖、相鄰 reader/parser、錄製摘要與相關 HAR event、兩份 DOM；跳過其他領域與靜態資源。

## 驗收與驗證契約

- 工單完全相符且唯一；備註非空列保留四個指定欄位；空白列排除。
- 全空白為 `count=0`、`records=[]`；跨頁讀取完整且分頁不一致時報錯。
- `python -m pytest tests/test_periodic_inspection_work_order_details.py -q`。
- `python -m pytest -q`、`python -m compileall -q src/mmis_connector/periodic_inspection tools/mmis_development/query_periodic_inspection_work_order_details.py`、`git diff --check`。
- 即時唯讀查詢 `115-2A-69254-001`；CLI 無 UI 截圖需求。

## 完成證據

見 `verification/MMIS-039.md`。
