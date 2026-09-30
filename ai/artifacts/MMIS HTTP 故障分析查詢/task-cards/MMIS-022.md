# AI-Ready 任務卡

## Metadata

- 任務：實作 HTTP-only 故障分析查詢工具
- 上層規格：`ai/artifacts/MMIS HTTP 故障分析查詢/feature-spec.md`
- 上層 Epic：MMIS HTTP 故障分析查詢
- 上層 User Story：查詢故障分析
- 分軌：後端
- 前置任務（dependsOn）：MMIS-001、MMIS-002（皆 done）
- 狀態：完成（2026-09-30）
- 風險等級：高（認證與內部網路唯讀存取）
- Agent owner：Codex
- 人工核准者：專案使用者（2026-09-30 明確要求開發）

## 目標與需求

建立 `python -m tools.mmis_development.query_fault_notice_analysis <通報號>`，以純 HTTP 完成唯一篩選、進入明細、開啟故障分析與五欄擷取，只輸出 stdout JSON。

- 動態解析 table prefix、通報號欄、detail link、故障分析 tab 與五個 label/textarea。
- 輸入驗證與唯一、完全相符、單頁結果保護。
- 五欄保留空白與多行文字；缺欄 fail closed。
- 不新增瀏覽器、檔案輸出、遠端寫入或 production-to-tools 依賴。

## 驗收標準

- 錄製中的動態表格第 14 欄不被寫死，測試以 semantic header 定位。
- event 順序為 filter、detail click、analysis tab click，xhr 連續。
- 範例 DOM 的五欄內容完整解析；空白為 `""`。
- 錯誤路徑不輸出部分成功資料或敏感資訊。
- 針對性、完整回歸、compileall、pip check、diff check 與審查關卡通過。

## 驗證契約

- 單元／整合：`tests/test_read_fault_notice_analysis.py`、tool/public API/architecture 回歸。
- E2E：離線檢查完成後，執行一次 `1150828-12` 唯讀 live 查詢；若環境阻擋則明確記錄。
- Build/Lint：`python -m compileall -q src tests tools/mmis_development`、`git diff --check`。
- 安全：掃描瀏覽器依賴、敏感值、recording/session 檔、檔案寫入與依賴方向。
- 螢幕截圖：不適用，無 UI 變更。

## 完成證據

- 變更：新增 fault-notice Reader、薄 development tool、semantic parser 與對應 tests/docs/governance。
- 測試：`153 passed, 4 skipped`；skips 皆為與本功能無關的既有 optional recordings。
- 其他：compileall、pip check、diff check、安全與依賴邊界掃描通過。
- Live：`1150828-12` 返回 success，五欄與錄製案例完整相符，無遠端寫入。
- 螢幕截圖：不適用。
- 已知限制：依賴 MMIS 可見標籤、label/for 與 Maximo event/table 結構；漂移時 fail closed。
- 後續任務：本卡無必要後續任務；寫入三欄屬另一個需單獨規格與 mutation 審查的功能。

## 情境包邊界

- 允許：`fault_notices/reader.py`、`parser.py`、public export、development tool/README、tests、architecture/context/governance artifacts。
- 禁止：`.env`、外部 recording、遠端 mutation、瀏覽器、既有命令契約、不相關使用者修改。
- 未知：live 權限與未來 DOM 漂移；透過唯一 semantic 解析與 fail-closed 控制。
