# 功能規格書

## Metadata

- 功能：查詢故障通報關聯的 ATP 故障分析
- 狀態：使用者於 2026-10-02 明確要求開發
- 風險等級：高（既有登入與內網唯讀 HTTP 查詢）

## 目標與行為

輸入一個通報號，精確查得一筆故障通報；先檢查明細中的「ATP故障」勾選狀態。若未勾選，直接以非零退出碼輸出 JSON 訊息「此故障通報未勾選ATP故障」。若已勾選，依序開啟「故障分析」與「故障分析-ATP」，只讀取「ATP故障分析」區段的故障要因、故障因子、故障項目。這三欄若為空值，保留為空字串。

## API 與驗收

- 指令：`python -m tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice <通報號>`。
- 通報號格式：七位數字、連字號、兩位數字；格式錯誤應在登入前拒絕。
- 成功 stdout：JSON，含 `success`、`query_name`、`fault_notice`、`analysis`；`analysis` 只含上述三欄。
- 查無、非唯一、未勾選、欄位缺失或頁面漂移時：JSON 錯誤及非零退出碼，不輸出部分成功資料。
- 全流程使用既有 `MMISSession` / `MaximoEventClient`，不啟動瀏覽器，不產生結果檔。

## 非目標與安全

- 不修改 MMIS 資料，不查詢選項清單中的所有可選值，只讀取目前所選內容。
- 不輸出故障點、故障作為、故障品處理、故障項目備註。
- 不將工具加入正式 CLI，不複製 HAR、session、憑證或查詢結果入版控。
- 重用既有同源 HTTPS、CSRF、page state 與憑證載入機制。
