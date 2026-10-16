# 驗證報告

## 摘要

- 任務：ATP 故障分析 AI 分類建議（測試階段）
- 結果：通過；已完成 mock 測試與指定通報的唯讀 Live 執行
- 驗證者：Codex，2026-10-16

## 指令與結果

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest --disable-warnings` | 316 passed，39 skipped | 包含 ATP 觸發矩陣、合法路徑、資料隔離、錯誤保留與既有功能回歸；skipped 為既有錄製資料未提供等條件 |
| `python -m compileall -q src tools/mmis_development tests` | exit 0 | Python 語法檢查 |
| `python -m pip check` | No broken requirements found | 依賴檢查 |
| `git diff --check` | exit 0 | 無 diff 空白錯誤 |
| `git hash-object data/atp_fault_analysis_options.json` 與 `git rev-parse HEAD:atp_fault_analysis_options.json` | 兩者皆 `470b2f23bf4df8315abeaaf5652867a4a21a4103` | 選項 JSON 搬移前後位元內容一致 |
| `python -m tools.mmis_development.query_fault_notice_full_detail 1151012-36 --ai-analysis` | 成功 | 實際執行；輸出經 PowerShell 擷取相關欄位，完整結果在程序內保留 |

## 指定通報的實際結果

- 通報號：`1151012-36`；`是ATP故障: true`。
- MMIS 原分類：`非ATP故障 → 非ATP故障 → 非ATP故障`。
- ATP AI 建議：`非ATP故障 → 非ATP故障 → 地上設備故障`。
- 建議路徑存在於完整選項 JSON 的對應父子分支，並已通過 Python 驗證。
- 原有「故障分析」含事故現象、處理概況及 AI 產生的故障原因、處理情形、改善對策。
- ATP AI 建議與 MMIS 原分類不同，原分類未被覆蓋。

## 審查發現

- ATP Prompt 接收同一份完整通報及工單素材；程式排除 MMIS 原 ATP 三欄、ATP 完整度狀態與先前 AI 三欄結論。
- 完整選項檔缺失或遍歷狀態不完整會明確失敗，沒有硬編碼補值。不同分支的同名選項以完整路徑驗證；同層重名檔案拒絕載入。
- ATP 分類格式或路徑錯誤最多重新生成一次，失敗只加錯誤欄位；既有 JSON 與原 AI 分析保留。
- 新流程沒有 MMIS 寫入呼叫，也沒有新增業務資料更新事件。密鑰仍由既有環境設定載入，錯誤欄位只含固定診斷訊息。
- 正式程式未引用 `mmis-post-feature-refactoring-guide.md`。`README.md` 與 `tools/mmis_development/README.md` 均未修改。

## 殘留風險

- 這是單筆 Live 驗證；模型對其他 ATP 案件的分類品質仍須後續人工抽樣驗收。
- 兩份 README 依本次禁止修改要求維持原樣，其中 development README 仍提及舊的選項輸出路徑；目前程式與測試均使用新路徑。
- 沒有下層選項的分支目前只以合成測試驗證；現有完整 MMIS 匯出樹的 65 條路徑都有第三層項目。

## 後續

- 未來自動填報可重用載入、Prompt、解析與路徑驗證元件，再另行建立差異審核及經授權的 MMIS 寫入流程；本次沒有實作。
