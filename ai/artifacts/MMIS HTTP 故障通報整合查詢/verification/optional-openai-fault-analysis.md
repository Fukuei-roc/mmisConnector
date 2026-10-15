# 驗證報告：可選的 OpenAI 故障分析

## 變更與範圍

- 在完整通報開發工具加入 `--ai-analysis`，於原 MMIS 查詢完成後呼叫 OpenAI。
- 新增可重用分析元件、獨立 User Prompt、環境設定範例與相關文件。
- 原 MMIS Query、Reader、素材擷取邏輯及正式 auto-link 未修改。

## 執行證據

| 指令 | 結果 |
|---|---|
| `python -m pytest` | 257 passed, 34 skipped；skip 為缺少本機錄製 evidence 的既有測試 |
| `python -m compileall -q src tests tools/mmis_development` | 通過，無輸出 |
| `python -m pip check` | No broken requirements found |
| `git diff --check` | 通過；僅出現 Git 的 CRLF 換行提示 |
| `git check-ignore -v .env .env.example` | `.env` 被忽略；`.env.example` 由例外規則允許追蹤 |
| `python -m tools.mmis_development.query_fault_notice_full_detail bad-notice --ai-analysis` | exit 1；stdout 為單一 JSON 錯誤物件，於登入前拒絕錯誤通報號 |

## 審查備註

- API Key 來自環境或未追蹤 `.env`，設定不在錯誤訊息輸出。
- `store=False`；MMIS 原始 JSON 只在明確旗標下傳至 OpenAI。
- 暫時性錯誤最多額外重試兩次，永久錯誤無重試；會尊重合理的 Retry-After。
- 內容格式錯誤最多重新生成一次，失敗時不輸出部分結果。
- 沒有執行真實付費 API 或內網 MMIS 端到端測試；需由具有權限的使用者驗收。
