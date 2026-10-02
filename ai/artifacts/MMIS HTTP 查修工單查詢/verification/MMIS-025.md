# 驗證報告

## 摘要

- 任務：HTTP-only 查修工單查詢
- 結果：通過
- 驗證者：Codex，2026-10-02

## 指令與證據

| 指令 | 結果 | 備註 |
|---|---|---|
| `python -m pytest -q` | 通過 | 全套測試通過、8 skipped；錄製 DOM 與空值、多頁、非 CA、去重、錯誤路徑測試通過 |
| `python -m compileall -q src tools/mmis_development tests` | 通過 | 無編譯錯誤 |
| `git diff --check` | 通過 | 無 whitespace 錯誤 |
| `python -m tools.mmis_development.query_repair_work_orders_linked_to_fault_notice 1150930-09` | 通過 | stdout JSON `count=1`，工作單 `115-CA-40035`、檢修日期 `2026/09/30` |

## 審查與殘留風險

- HAR 最後頁簽 click 回應包含 `查修工單`；DOM 十欄與截圖日期一致。程式只使用既有登入及唯讀 Maximo event，不保存憑證或查詢結果。
- 多頁、空表僅有離線測試；未來 MMIS 表格名稱或結構改變時會明確報錯。
- UI 未變更，螢幕截圖交付不適用；外部錄製截圖僅用於核對資料。
