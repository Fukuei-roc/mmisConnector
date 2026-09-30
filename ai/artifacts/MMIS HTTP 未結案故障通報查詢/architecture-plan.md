# 架構筆記

## 決策

- 在既有 `src/mmis_connector/fault_notices/query.py` 增加正式的 `UnclosedFaultNoticeQuery`，不建立第二套 HTTP client。
- 將同檔案內既有 app 載入、saved-query 選取與完整分頁收集邏輯收斂為私有共用基底，保持 `UnprocessedFaultNoticeQuery` 公開契約不變。
- 由 `parse_maximo_table_schema()` 解析動態 table prefix 與「事故等級」「配屬段別名稱」欄位，不保留錄製中的動態 ID。
- 重用 `MaximoEventClient.post_events()` 送出錄製確認的 event 序列；wrapper 只處理零參數驗證、登入、呼叫與 stdout JSON。
- 不新增正式 production CLI subcommand、外部依賴、資料庫、檔案輸出或瀏覽器 fallback。

## 契約

- 入口：`python -m tools.mmis_development.query_unclosed_fault_notices`
- 輸入：無位置參數；認證沿用環境設定。
- 固定條件：「故障通報未結案清單」、`配屬段別名稱=新竹機務段`、`事故等級=A,B`。
- 成功：`success`、`query_name`、`filters`、`count`、`records`。
- 失敗：非零 exit code 與去敏 JSON 錯誤。
- 不建立任何輸出檔案。

## 預期變更

- `src/mmis_connector/fault_notices/query.py`
- `src/mmis_connector/__init__.py`
- `tools/mmis_development/query_unclosed_fault_notices.py`
- `tools/mmis_development/README.md`
- `tests/test_query_unclosed_fault_notices.py`
- `tests/test_development_tools.py`
- `tests/test_public_api.py`
- `tests/test_architecture.py`
- 對應 governance、context 與 verification artifacts

## 風險與控制

- 高風險來源為 MMIS 認證與內部網路讀取；本功能不執行 mutation。
- 所有 Maximo POST 沿用既有不自動重試 transport。
- 不輸出帳密、cookie、CSRF、session id、page URL、動態 ID 或原始回應。
- HTTP 200 後仍驗證查詢名稱、schema、分頁連續性、固定 total 與最終資料列數。
- 回滾不涉及資料遷移；可移除新增 Query、tool、tests 與 export。

## 驗證策略

- 先以 fake event responses 驗證動態欄位、事件順序、零筆／單頁／多頁與 fail-closed 錯誤。
- 以本機 optional recording 驗證 2026-09-30 DOM 的 20/31 結構，但不提交 evidence。
- 執行完整 pytest、compileall、pip check、diff check 與安全性／依賴邊界掃描。
- 離線驗證通過後執行一次唯讀 live 命令。

## 審查關卡

- 產品：2026-09-30 人工核准。
- 架構：須確認只重用既有 domain／transport／parser，production 不依賴 tools。
- 安全性：須確認固定同源、秘密不落盤／不輸出、無瀏覽器 fallback、無 mutation。
- 測試：須覆蓋 event sequence、完整分頁與錯誤路徑。
- UI：不適用。
