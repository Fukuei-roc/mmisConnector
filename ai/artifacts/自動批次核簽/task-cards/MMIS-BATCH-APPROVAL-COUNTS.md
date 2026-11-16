# 任務卡 MMIS-BATCH-APPROVAL-COUNTS

- 上層規格：`ai/artifacts/自動批次核簽/feature-spec.md`。
- User Story：以副段長帳號取得各類待簽核數量。
- 分軌：後端 CLI。
- 前置任務：無。
- 狀態：實作完成，待人工驗收。
- 風險等級：高。
- 人工核准狀態：使用者於 2026-11-16 明確要求實作與驗證本步驟。

## 情境包

- 既有模式：`MMISConfig`、`MMISSession`、`MaximoEventClient.load_app_with_response` 與 `run_json_tool`。
- 錄製證據：`2026-11-16_uto-batch-approve-work-orders` 的 HAR、DOM 與 timeline。
- 允許變更：登入環境變數選擇、批次核簽解析模組、CLI、環境變數範例、對應測試與本 Epic 產出物。
- 未知事項：MMIS 日後可能更改頁籤標題或類型。

## 驗收與驗證契約

- 輸出含 17 個指定類型，數量為整數。
- 帳號必須為指定副段長帳號。
- 缺漏類型或錯誤頁面須拒絕輸出成功數據。
- 執行單元測試、錄製 DOM 測試、實際 CLI 查詢及 `git check-ignore .env`。
- 不涉及新 UI，無新增畫面截圖。

## 後續任務

待使用者提供後續批次核簽操作步驟後，再建立獨立任務卡。
