# 驗證報告：準備移除五個重複查詢入口

## 摘要

- 結果：通過。五個入口檔仍在，正式功能程式未修改。
- 驗證者：Codex。

## 指令與結果

| 指令 | 結果 |
|---|---|
| `python -B -m pytest tests/test_development_tools.py tests/test_architecture.py tests/test_fault_notice_full_detail.py tests/test_daily_inspection_inspection_records.py -q -o addopts='' -p no:cacheprovider` | 51 passed，7 skipped |
| `python -B -m pytest -q -o addopts='' -p no:cacheprovider` | 604 passed，48 skipped |
| 在 `sys.meta_path` 阻擋五個待刪模組 import 後執行同一完整測試集 | 604 passed，48 skipped |
| `rg` 精確搜尋五個模組名稱，排除入口自身與歷史看板卡片 | 現行程式、測試與指令文件無引用 |
| `git diff --check` | 通過 |

以上 pytest 指令設定 `PYTHONDONTWRITEBYTECODE=1`，避免產生新的 bytecode。跳過的測試主要依賴本機錄製證據，本次沒有執行 MMIS Live 操作。

模擬刪除的測試在 PowerShell 執行下列程式，禁止五個模組被 import，但不移動或刪除檔案：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$code = @'
import sys
from importlib.abc import MetaPathFinder
import pytest

blocked = {
    'tools.mmis_development.query_fault_notice_analysis',
    'tools.mmis_development.query_atp_fault_analysis_linked_to_fault_notice',
    'tools.mmis_development.query_work_orders_linked_to_fault_notice',
    'tools.mmis_development.query_repair_work_orders_linked_to_fault_notice',
    'tools.mmis_development.query_daily_inspection_work_order_by_number',
}

class BlockRetiredTools(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in blocked:
            raise ModuleNotFoundError(f'blocked planned removal: {fullname}')
        return None

sys.meta_path.insert(0, BlockRetiredTools())
sys.exit(pytest.main(['-q', '-o', 'addopts=', '-p', 'no:cacheprovider']))
'@
python -B -c $code
```

## 審查發現

- 沒有更改 `src/mmis_connector/`、MMIS 網路操作、資料庫或寫入邏輯。
- 現行測試已驗證完整通報的故障分析、ATP 分析、段修及 CA 工單，以及日檢明細的已勾稽通報。
- 歷史規格與看板卡片仍記錄舊入口，作為當時驗證證據，不作現行執行依賴。

## 殘留風險

- Repo 之外的排程、人工腳本或捷徑無法由這次掃描確認。
- 完整查詢的 JSON 形狀與單項入口不同；若外部呼叫者讀取舊格式，刪除前需遷移。
- 五個入口尚未刪除，這次只驗證 repo 內可刪除的前置條件。
