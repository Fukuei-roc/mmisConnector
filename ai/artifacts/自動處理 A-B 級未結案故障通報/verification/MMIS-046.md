# 驗證報告

## 摘要

- 任務：MMIS-046 查詢首筆通報並回填六個結案狀態檢查值
- 結果：通過（離線）；Live MMIS 未執行
- 驗證者：Codex

## 指令

| 指令 | 結果 | 備註 |
|---|---|---|
| 唯讀 SQLite 查詢 `data/unclosed_ab_fault_notices.db` | 通過 | 32 筆、15 欄；六個檢查欄位各為 0 筆非 NULL，確認既有問題 |
| `python -m pytest` | 通過 | 389 passed, 39 skipped |
| `python -m compileall -q src tests` | 通過 | 無輸出 |
| `python -m compileall -q tools/mmis_development` | 通過 | 無輸出 |
| `python -m pip check` | 通過 | No broken requirements found. |
| `git diff --check` | 通過 | 僅 Windows 換行提示 |

## UI 證據

| Viewport | 螢幕截圖 | 備註 |
|---|---|---|
| 不適用 | 不適用 | 無 UI 變更 |

## 審查發現

| 發現 | 嚴重程度 | 狀態 |
|---|---|---|
| 主指令只執行 snapshot，完整通報函式未接入 | 中 | 已修正，離線測試驗證第一筆回填 |
| 第一欄預設需要付費 AI 才能取得布林值 | 中 | 預設維持 NULL；新增明確 `--check-analysis-readiness` opt-in |
| 單筆明細或 SQLite 更新失敗可能留下不完整結果 | 中 | 保留已完成 snapshot；錯誤 JSON 標明階段，單筆更新 transaction rollback |

## 殘留風險

- 未自行執行 Live MMIS。使用者先前執行產生的 32 筆仍是修正前資料，需重新執行新程式才會回填第一筆。
- 預設模式只有五個非 NULL 檢查值；`Sufficient Data for Fault Analysis` 固定為 NULL。啟用旗標會產生 OpenAI API 費用並傳送事故與相關工單素材。
- 第二筆以後的六個欄位維持 NULL，符合開發階段只處理第一筆的限制。
