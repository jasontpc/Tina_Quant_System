# Tina Quant System — Paper Trade Optimization Plan
# Goal: Enable multiple teams to paper trade, daily review, and continuous improvement

## Phase 1: Immediate Fixes (Today)

### 1. Exit Logic Enhancement
**Problem:** No exits triggered despite 21 positions with >10% profit and RSI>80 in market.

**Fix in leos_v65.py:**
```python
# Add to exit conditions:
elif rsi > 80 and pnl_pct > 5:
    reason = 'overbought_profit_lock'
```

**Why:** When market is overbought (RSI>80), existing positions with >5% profit should be locked in. No new entries when overbought, but EXISTING profits must be protected.

### 2. Position Limit Per Stock
**Problem:** 31 positions in single stock (3034) defeats diversification.

**Fix:**
```python
MAX_POSITIONS_PER_STOCK = 3  # Max 3 positions per symbol
```

### 3. Duplicate Entry Prevention
**Problem:** System keeps adding same signal repeatedly.

**Fix:** cooldown already exists (60 min) but positions accumulate. Need to track total open positions and max total exposure.

---

## Phase 2: Daily Automated Review (Tomorrow)

### Daily Paper Trade Report
```python
# leos_daily_review.py — runs every morning before market open
# - Check all open positions
# - Flag: near target, near stop, overbought with profit
# - Auto-exit if conditions met
# - Generate daily stats and send to Telegram
```

### Automated Exit Rules
| Condition | Action |
|:----------|:-------|
| Price >= Target | Exit (take profit) |
| Price <= Stop | Exit (stop loss) |
| RSI > 80 AND profit > 5% | Exit (lock in profit) |
| RSI > 90 AND profit > 2% | Exit (extreme overbought) |
| Hold days > MAX_HOLD_DAYS | Exit (time limit) |

---

## Phase 3: Multi-Team Paper Trade Platform

### Architecture
```
tina_paper_trade/
├── unified_trades.json        # All teams' positions
├── teams/
│   ├── leo/                  # Leo's strategies
│   ├── nana/                 # Nana's strategies
│   └── ray/                  # Ray's strategies
├── daily_review.py           # Automated daily review
├── performance_tracker.py    # Stats, PnL, win rate
└── telegram_report.py        # Daily summary to all teams
```

### How teams join
1. Fork the system or connect via API
2. Each team has own strategy params
3. All paper trades recorded in unified_trades.json
4. Daily report shows each team's performance
5. Failure analysis shared across teams

---

## Phase 4: Continuous Improvement

### Weekly Review Cycle
```
Every Sunday 10:00:
1. Analyze closed trades (wins/losses/patterns)
2. Update strategy params based on what worked
3. Document failures in failure DB
4. Push param updates to all teams
```

### Failure Analysis System
- Track every losing trade
- Categorize failure type (wrong entry, exit too early, news event, etc.)
- Feed insights back into strategy improvement

---

## Immediate Actions

### Today - Fix Leo Exit Logic
```python
# Add to leos_v65.py exit conditions (around line 250):
elif rsi > 80 and pnl_pct > 5:
    reason = 'overbought_profit_lock'
elif pnl_pct > 15:
    reason = 'big_gain_take_profit'  # Lock in 15%+ gains
```

### Tomorrow - Run Daily Review
- Schedule leos_daily_review.py at 09:00 daily
- Send Telegram report with:
  - Overnight changes
  - Positions to watch
  - Auto-exits executed
  - Day's net PnL

### This Week - Build Unified Platform
1. Create `tina_paper_trade/` structure
2. Migrate Leo/Nana/Ray paper trades to unified format
3. Build web dashboard (Streamlit) for all teams to view
4. Add multi-team Telegram groups

---

## Success Metrics
- All 106 positions reviewed and acted upon
- Win rate > 60% on closed trades
- Average trade duration < 10 days
- Daily automated reports sent without failure
- Multiple teams using the system simultaneously