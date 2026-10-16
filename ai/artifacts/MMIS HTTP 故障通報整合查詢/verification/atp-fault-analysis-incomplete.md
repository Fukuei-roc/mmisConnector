# ATP 故障分析未填妥狀態驗證

- 變更：完整通報 CLI 的 `結案狀態檢查` 新增 `ATP Fault Analysis Incomplete`，位置緊接 `CA Repair Work Orders Not Closed`。未勾選 ATP 時為 `false`；已勾選且故障要因、故障因子或故障項目任一為空或純空白時為 `true`。
- 指令：`python -m pytest tests/test_depot_work_order_status.py tests/test_fault_notice_analysis_materials.py tests/test_fault_notice_ai_analysis.py -q`
- 結果：exit code 0，目標測試全數通過；包含三欄逐一空值、純空白、三欄齊全及 JSON 順序。
- 指令：`python -m pytest -q`
- 結果：exit code 0；全套測試通過，既有測試中有跳過項目。
- 指令：`git diff --check`
- 結果：exit code 0，無空白錯誤；Git 顯示 Windows 工作樹換行格式提示。
- 安全性：僅依既有 reader 輸出計算，不增加 MMIS 網路事件或遠端寫入，不儲存查詢資料。
- 已知限制：未執行即時 MMIS 查詢；線上頁面內容與授權狀態未在本次驗證。既有 parser 若無法解析 ATP 欄位，仍依既有錯誤路徑退出。
- 後續任務：無。
