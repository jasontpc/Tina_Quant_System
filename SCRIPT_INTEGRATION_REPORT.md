# Tina 全團隊腳本整合報告
**Date: 2026-05-09**
**Total Scripts: 430+**

---

## 橫向整合（跨 Team 重複）

### 1. MARGIN 數據腳本 — 10 個 → 整合至 1 個核心

| 現況腳本 | 大小 | 評估 |
|:--------|-----:|:-----:|
| `tw_margin/tw_margin_database.py` | 15,419 | ⭐ **MAIN** — 完整功能 |
| `scripts/fetch_twse_margin.py` | 5,788 | ⚠️ **重疊** — 可併入 main |
| `scripts/fetch_margin_finmind.py` | 4,729 | ⚠️ **重疊** — 可併入 main |
| `scripts/check_tw_margin.py` | 3,394 | 🔧 **工具** — 保留（輕量檢查） |
| `scripts/fetch_margin_data.py` | 1,746 | ❌ **重疊** — 廢棄 |
| `tw_margin/tw_margin_daily.py` | 1,594 | ❌ **重疊** — 廢棄 |
| `inspect_tw_margin.py` | 861 | 🔧 **工具** — 保留（快速檢視） |
| `scripts/check_margin_db.py` | 1,270 | ❌ **重疊** — 廢棄 |
| `us_margin/us_margin_database.py` | — | ⭐ **MAIN (US)** — 獨立系統，保留 |
| `us_margin/us_margin_daily.py` | 4,477 | 🔧 **工具** — 保留 |

**整合方案：** `fetch_twse_margin.py` + `fetch_margin_finmind.py` → 合併進 `tw_margin_database.py`

---

### 2. BACKTEST 系統 — 25 個 → 整合至 3 個核心

| 現況 | 腳本 | 評估 |
|:-----|:-----|:-----:|
| **主系統** | `scripts/tina_backtest_engine.py` | ⭐ MAIN — 標準回測引擎 |
| **驗證器** | `scripts/tina_backtest_validator.py` | ⭐ MAIN — 驗證機制 |
| **沙盒** | `scripts/brain_backtest_sandbox.py` | ⭐ MAIN — 智能學習沙盒 |

**廢棄候選（22個）：**
- `backtest/v3_full_backtest.py`, `v41_backtest.py`, `v42_q1_backtest.py`
- `backtest/rolling_backtest_v4.py`, `rolling_backtest_simple.py`
- `backtest/top100_kdj_macd_backtest.py`
- `backtest/cycle9_steps4_5_backtest.py`
- `master_backtest.py`
- `automation/full_backtest_optimizer.py`
- `teams/maggy/scripts/maggy_backtest*.py` (3個)
- Plus 10+ more

---

### 3. HEALTH_CHECK — 6 個 → 整合至 1 個核心

| 現況腳本 | 大小 | 評估 |
|:--------|-----:|:-----:|
| `scripts/full_health_check.py` | 10,552 | ⭐ **MAIN** — 最完整 |
| `scripts/db_health_check.py` | 5,914 | 🔧 **工具** — 快速檢查，保留 |
| `automation/system_health_check.py` | — | ❌ **重疊** — 廢棄 |
| `backtest/api_health_check.py` | — | ❌ **重疊** — 廢棄 |
| `scripts/us_health_check.py` | — | ❌ **重疊** — 廢棄 |
| `tina_health_check.py` | — | ❌ **重疊** — 廢棄 |

---

### 4. TINA_BRAIN — 12 個 → 整合至 4 個核心

| 現況腳本 | 評估 |
|:--------|:-----:|
| `scripts/tina_brain_core.py` | ⭐ MAIN — 核心引擎 |
| `scripts/tina_brain_learner.py` | ⭐ MAIN — 學習模組 |
| `scripts/tina_brain_gap_analysis.py` | ⭐ MAIN — 差距分析 |
| `scripts/tina_brain_report.py` | ⭐ MAIN — 報告輸出 |

**廢棄（8個，全部在 `scripts/_TRASH_/`）：**
```
tina_brain_defect_check.py, tina_brain_dispatcher.py, tina_brain_etf.py,
tina_brain_evolution_report.py, tina_brain_logic_overview.py,
tina_brain_scheduler.py, tina_brain_v3.py
```

---

### 5. LEO 系統 — 45 個 → 整合至 4 個核心

| 現況腳本 | 大小 | 評估 |
|:--------|-----:|:-----:|
| `teams/leadtrades/leos/leos_v65.py` | 25,730 | ⭐ **MAIN** — 活躍 Cron |
| `teams/leadtrades/leos/leo_institutional_flow.py` | 11,907 | ⭐ **MAIN** — 法人流向 Cron |
| `teams/leadtrades/leos/leos_daily_review.py` | 37,885 | ⭐ **MAIN** — 每日複審 |
| `teams/leadtrades/leos/leo_core_analysis.py` | 14,566 | ⭐ **MAIN** — 核心分析 |
| `teams/leadtrades/leos/leo_v70.py` | 11,841 | 🔄 **NEXT** — 待啟用 v7.0 |
| `teams/leadtrades/leos/leo_autonomous_v2.py` | 11,761 | 🔧 **備用** — 保留 |
| `teams/leadtrades/leos/leo_autonomous_ai_chain.py` | 10,231 | 🔧 **實驗** — 保留 |

**廢棄候選（38個）：**
- `leo_perf.py`, `leo_perf_calc.py`, `leo_perf_since.py`, `leo_performance_tracker.py` → 整合至 `leo_performance_log.md`
- `check_leo_db.py`, `check_leo_db2.py`, `check_leo_db3.py` → 廢棄
- `leo_autonomous_*.py`（多個版本）→ 整合至 `leo_autonomous_v2.py`

---

### 6. RAY 系統 — 25 個 → 整合至 3 個核心

| 現況腳本 | 評估 |
|:--------|:-----:|
| `teams/ray/dca_market_brief.py` | ⭐ **MAIN** — 活躍 Cron |
| `teams/ray/ray_autonomous_trader.py` | 🔄 **升級** — 可取代 dca_market_brief |
| `teams/ray/ray_etf_dca.py` | 🔧 **工具** — DCA 計算 |

**廢棄候選（22個）：**
- 各種 `ray_*.py` 測試版本

---

### 7. MARGIN DB 重疊（宏觀法人）

| DB | 使用腳本數 | 問題 |
|:---|:---:|:-----|
| `data/macro_institutional.db` | 7 | 讀寫者眾多，需統一介面 |

---

## 縱向整合（Pipeline 上下游）

###  Pipeline A: 每日晨報
```
tina_daily_morning_report.py (4358)
    ↓
macro_data_fetcher.py → reports/macro/{date}_morning.json
    ↓
tina_daily_brief.py (6098) ← 兩個腳本功能重疊！
```
**整合：** `tina_daily_morning_report.py` 合併進 `tina_daily_brief.py`

### Pipeline B: 收盤流程
```
16:00 — stock_tracking_update.py + stock_signal_scanner.py + trade_journal.py
16:30 — log_review.py --mode evening
17:00 — tina_strategy_reviewer.py
```
**問題：** 三個腳本分散，可考慮整合為一個 `closing_pipeline.py`

### Pipeline C: 法人流向
```
leo_institutional_flow.py (法人流向分析)
    ↓
institutional_flow_analyzer.py (腳本同目錄，內容重疊)
```
**整合：** `institutional_flow_analyzer.py` 合併進 `leo_institutional_flow.py`

---

## 記憶/增智腳本連結圖

```
stores/
├── brain_memory_cli.py      ← 大腦 CLI 入口
│   └── 调用...
├── memory_distiller.py      ← 每日蒸餾（cron: 20:00）
├── memory_writer.py         → 寫入 stores/short_term/
├── long_term_writer.py      → 寫入 stores/long_term/
├── accumulated_wisdom.py    → stores/long_term/accumulated_wisdom.json
│
scripts/
├── tina_brain_core.py        ← 大腦核心邏輯（被 streamlit_tw_stock.py 調用）
├── tina_brain_learner.py     ← 增量學習（被 tina_autonomous_learning.py 調用）
├── tina_brain_gap_analysis.py ← 差距分析（被 tina_autonomous_learning.py 調用）
├── tina_brain_report.py      ← 報告生成（被 cron 調用）
├── tina_autonomous_learning.py ← 主學習引擎（cron: 17:00 Fri）
│   ├── tina_brain_learner.py
│   └── tina_brain_gap_analysis.py
├── tina_autonomous_decision.py ← 決策引擎（cron: 每3hr）
│   └── tina_decision_trigger.py
├── tina_decision_db.py       ← 決策記錄庫
├── tina_decision_logger.py   ← 決策日誌
└── tina_decision_trigger.py  ← 決策觸發器

Brain → Streamlit 調用鏈:
streamlit_tw_stock.py
  → fetch_institutional (FinMind + INST_CACHE)
  → fetch_price (Shioaji優先 → yfinance備用)
  → Tina-MemoryUtils.psm1 → Write-TinaMemory
```

**記憶系統完整性：** ✅ 結構清晰，無重疊

---

## 執行方案

### Phase 1 — 立即清理（安全，無風險）
```
1. 刪除 scripts/_TRASH_/ (8個 tina_brain 廢腳本)
2. 刪除 check_leo_db.py, check_leo_db2.py, check_leo_db3.py
3. 刪除重複的 health_check 廢腳本
```

### Phase 2 — 腳本整合（需要測試）
```
4. 合併 fetch_twse_margin.py + fetch_margin_finmind.py → tw_margin_database.py
5. 合併 tina_daily_morning_report.py → tina_daily_brief.py
6. 合併 institutional_flow_analyzer.py → leo_institutional_flow.py
```

### Phase 3 — 系統重構（需要 Jo 確認）
```
7. 廢棄 22 個 backtest 腳本 → 統一至 tina_backtest_engine.py
8. 廢棄 38 個 leo 廢腳本 → 統一至 leos_v65.py
9. Ray: 評估 ray_autonomous_trader.py 是否取代 dca_market_brief.py
```

---

**需要 Jo 確認：Phase 1 可以現在執行，Phase 2-3 需要什麼時候處理？**