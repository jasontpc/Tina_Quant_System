# Nana 活躍腳本清單 (ACTIVE_SCRIPTS)

**更新時間：** 2026-05-08  
**狀態：** ✅ P0 清理完成

---

## ⭐ 活躍腳本（已被 Cron 使用）

| 腳本 | 功能 | Cron Job | 頻率 |
|:-----|:-----|:---------|:-----:|
| `nana_v68.py` | 波段交易旗艦 | `faf759b4` | 5次/日 |
| `nana_db_update.py` | 資料庫更新 | — | 每日 |

---

## 📋 Cron Job 對照

| Job ID | 腳本 | 功能 |
|:-------|:-----|:-----|
| `faf759b4` | `nana_v68.py` | Nana 波段v6.4 |
| `bb513ff7` | ? | Nana 週報 |
| `2900550c` | ? | Nana 月報 |

---

## 🔒 Archive 內容

### archive/（8 個 Python 版本）

```
nana_v64.py, nana_v65.py, nana_v66.py
nana_v2_full.py, nana_v2_optimizer.py, nana_v2_test.py
nana_system_v3.py, nana_system_v3_quick.py
```

### archive_json/（15 個 JSON 結果）

```
backtest_final.json, backtest_result.json, backtest_results.json
band_results.json, expanded_backtest.json, nana_backtest_learnings.json
optimization_result.json, optimization_results.json
scan_cache.json, scan_cache_v64.json, scan_cache_v68.json
scan_result.json, system_v3_results.json, test_result.json, v4_results.json
```

---

## 🚫 禁止事項

1. **禁止刪除 archive/ 或 archive_json/** — 歷史版本保留
2. **禁止修改 Nana v68 正式版** — 修改前先備份
3. **禁止新增 Cron Job** — 未經 Tina 委員會審批

---

## ✅ P0 清理記錄（2026-05-08）

| 行動 | 數量 |
|:-----|:----:|
| Python 版本移入 archive | 8 個 |
| JSON 結果移入 archive_json | 15 個 |

---

_Last update: 2026-05-08_
