# SYSTEM DEFECT REPORT & IMPROVEMENT PLAN
**Date:** 2026-05-13 21:00
**System:** Tina Quant System v3.13

---

## P0 DEFECTS (Must Fix Immediately)

### D1: Cron Governor State File Missing
- **File:** `stores/short_term/cron_governor_state.json`
- **Impact:** Cron Governor cannot track job health or detect errors
- **Root Cause:** `cron_governor.py` writes to file but file was never initialized
- **Fix:** Ensure `cron_governor.py` creates/updates state file on each run
- **ETA:** 1 day

### D2: ray_scheduler.py Missing
- **File:** `scripts/ray_scheduler.py`
- **Impact:** VRAM dynamic scheduling (每小時) is non-functional
- **Description:** Supposed to run every hour to switch 7B/4B models based on market hours (09:00-13:30 / 21:30-04:00 trade mode vs 14:00-20:00 training mode)
- **Fix:** Create `ray_scheduler.py` with `@ray_singleton`, reads schedule from config
- **ETA:** 1 day

### D3: experience_ledger.json Missing
- **File:** `stores/long_term/experience_ledger.json`
- **Impact:** No systematic learning from trade wins/losses
- **Description:** Jo expected this to track all trade outcomes for AI learning; referenced by Tina's SOUL.md but file does not exist
- **Fix:** Create `experience_ledger.json` schema with entries: `{id, date, symbol, action, cost, exit_price, pnl, pnl_pct, result, rsi_at_entry, holding_days, reason}`
- **ETA:** 1 day

### D4: patterns.json Empty (0 entries)
- **File:** `stores/long_term/patterns.json`
- **Impact:** Pattern detection system not building long-term memory
- **Description:** Should accumulate market patterns (≥3 observations → promotion to long-term). Currently 0 entries.
- **Fix:** Debug distillation job write logic; ensure `memory_distiller.py --level weekly` properly writes to patterns.json
- **ETA:** 1 day

---

## P1 DEFECTS (Should Fix Soon)

### D5: ray_distiller_auto.py Missing @ray_singleton
- **File:** `scripts/ray_distiller_auto.py`
- **Impact:** 05:00 physical distillation can collide with other Ollama scripts (VRAM conflict)
- **Fix:** Add `from utils.ray_guard import ray_singleton` + `@ray_singleton` decorator to `run_physical_distillation()`
- **ETA:** 30 min

### D6: macro_indicators_tracker.py Missing @ray_singleton
- **File:** `scripts/macro_indicators_tracker.py`
- **Impact:** Could collide with other Ollama scripts during macro analysis
- **Fix:** Add `ray_guard` import + `@ray_singleton` decorator to main function
- **ETA:** 30 min

### D7: wisdom_corrections.json Has Only 1 Insight
- **File:** `stores/long_term/accumulated_wisdom.json` (338 bytes)
- **Impact:** Ray Layer 3 macro analysis produces insights but not accumulating properly
- **Description:** Only 1 insight accumulated — system not properly storing macro analysis outputs
- **Fix:** Check `ray_us_premarket_macro.py` for proper write logic to accumulated_wisdom.json
- **ETA:** 1 day

### D8: lessons.json Has Only 2 Entries
- **File:** `stores/long_term/lessons.json` (3558 bytes)
- **Impact:** Learning system not fully operational
- **Description:** Should have separate win lessons (`wins/`) and loss lessons (`losses/`); currently only 2 entries
- **Fix:** Ensure distillation jobs properly categorize wins/losses as lessons
- **ETA:** 1 day

---

## P3 ARCHITECTURE GAPS

### G1: ray_knowledge_distiller.py Does Not Exist
- **File:** `scripts/ray_knowledge_distiller.py` (referenced in Jo's architecture)
- **Description:** 14:00 knowledge distillation script (separate from logic distillation)
- **Status:** Does not exist
- **ETA:** 1 day

### G2: ray_web_collector.py Does Not Exist
- **File:** `scripts/ray_web_collector.py` (referenced in Jo's architecture)
- **Description:** 17:00 supply chain mapping script
- **Status:** Does not exist
- **ETA:** 2 days

### G3: ray_us_premarket_macro.py May Be Incomplete
- **File:** `scripts/ray_us_premarket_macro.py`
- **Description:** 21:00 macro analysis takeover; cron job exists but script may be missing or incomplete
- **Status:** Needs verification
- **ETA:** 1 day

### G4: All 55 Ollama Scripts Need @ray_singleton
- **Description:** System-wide audit of Ollama-related scripts for VRAM protection
- **Currently found:** Only 4 ollama-related scripts (likely under-detected due to script naming)
- **Fix:** Full audit of scripts folder for `ollama`, `qwen`, `deepseek` references
- **ETA:** 3 days

---

## IMPROVEMENT PLAN (Priority Order)

| # | Priority | Title | ETA |
|:-:|:--------:|:------|:---:|
| IM1 | P0 | Fix Cron Governor State File | 1 day |
| IM2 | P0 | Create ray_scheduler.py | 1 day |
| IM3 | P0 | Create experience_ledger.json | 1 day |
| IM4 | P0 | Fix patterns.json Empty | 1 day |
| IM5 | P1 | Add @ray_singleton to ray_distiller_auto.py | 30 min |
| IM6 | P1 | Add @ray_singleton to macro_indicators_tracker.py | 30 min |
| IM7 | P2 | Fix wisdom_corrections accumulation | 1 day |
| IM8 | P2 | Create ray_knowledge_distiller.py | 1 day |
| IM9 | P3 | Create ray_web_collector.py | 2 days |
| IM10 | P3 | Create / verify ray_us_premarket_macro.py | 1 day |
| IM11 | P3 | Audit All Ollama Scripts for VRAM | 3 days |

---

## DATABASE INTEGRITY

| Database | Size | Status | Notes |
|:---------|-----:|:------:|:------|
| data/yfinance.db | 113MB | OK | US/TW price data |
| data/us_history.db | 27.5MB | OK | US stock OHLCV |
| data/tw_history.db | 9.5MB | OK | TW stock OHLCV |
| data/leverage_etf.db | 20MB | OK | Leveraged ETF data |
| data/sherry_etf.db | 10.8MB | OK | Sherry ETF analysis |
| data/macro_institutional.db | 10MB | OK | Institutional data |
| data/finmind.db | 860KB | OK | FinMind API data |
| data/master_backtest.db | 308KB | WARN | Small — may indicate incomplete data |
| data/sherry_backtest.db | 448KB | OK | Sherry backtest |
| data/tw_margin.db | 1.5MB | OK | TW margin data |
| teams/data/rsi_verification.db | 3.7MB | OK | RSI verification |

---

## SUSPECT DIRECTORIES (Should Clean Up)

| Directory | Status | Action |
|:----------|:------:|:-------|
| archive/ | EMPTY | Delete |
| streamlit_cloud_backup_20260509/ | 3 items | Consider deleting (old backup) |
| backup_20260502/ | 3 items | Consider deleting (old backup) |
| backups/ | 2 items | Consider deleting |
| matrix_results/ | 2 items | Investigate - may be temp files |
| distillations/ | 2 items | Investigate - may be temp outputs |
| Tina_Quant_System/ | 2 items | Investigate - possible nested repo |

---

_Report generated by Tina v3.6 System Audit_