# 故障分析填寫完成狀態驗證

- 變更：完整通報 CLI 依 MMIS 已解析的三欄計算 `Fault Analysis Completed`，並放在「故障分析素材」前。
- 指令：`python -m pytest tests/test_fault_notice_full_detail.py tests/test_fault_notice_analysis_materials.py tests/test_fault_notice_ai_analysis.py -q`
- 結果：測試通過；1 項既有錄製 fixture 測試因本機缺少舊錄製檔而跳過。新錄製 DOM 測試通過。
- 指令：`python -m tools.mmis_development.query_fault_notice_full_detail 1150907-78`
- 結果：exit code 0；三欄均有內容；`"Fault Analysis Completed": true` 位於 `"故障分析素材"` 前。
- 指令：`git diff --check`
- 結果：exit code 0，無空白錯誤。
- 安全性：沿用單一 MMIS session 與既有解析資料，沒有新增 MMIS 寫入、錄製資料或密鑰檔。
- 已知限制：若 MMIS 欄位缺失，既有 `parse_labeled_textareas` 會報錯，不輸出布林值；這保留現有 fail-closed 行為。
- 後續任務：無。
