
=== Cycle 20 System Review ===

## Root Cause Fix Status
[V] MarketData.close NULL (52%): FIXED - backfilled 730 days, now 99.9% valid
[V] DailyStats.close NULL (9 records): FIXED - synced from MarketData

## Scoring System Status (v7)
[V] ScoreVersion: v7 (inst=70%, tech=30%)
[V] Strategies: All 10 symbols have consistent weights
[V] Score range: 3-45, avg=21.8
[-] Signal dist: 59 neutral, 1 watch, 0 strong_buy (needs review)

## Stock Pool Scan Results
- Total symbols scanned: 51
- Strong Buy: 23 symbols (2379, 2451, 2458, 2474, 2884, 3413, 6230, 8081, etc.)
- Watch: 4 symbols (3231, 00646, 2382, 2454)
- Neutral: 17 symbols
- Avoid: 7 symbols

## Tier Strategy (Proposed)
- Tier1 (60d, 8% target, 5% stop): 0050, 0056, 00713
- Tier2 (30d, 12% target, 7% stop): 2330, 2382, 2454, 2317, 3034
- Tier3 (14d, 15% target, 8% stop): 2379, 2451, 2458, 2474, 2884, 3413, 6230, 8081, 1605, 2308

## Win Rate by Symbol
- 2382: 88.9% (best)
- 2330: 83.3%
- 2454: 83.3%
- 0050: 83.3%
- 3034: 81.8%
- 00662: 80.0%
- 00646: 75.0%
- 0056: 60.0% [WARNING]
- 00713: 45.0% [WARNING]
- 2317: 40.0% [WARNING]

## Issues to Address
1. 00713, 0056, 2317 have negative/low win rates - review strategy
2. DailyStats signal shows 59 neutral / 1 watch - no strong buy signals
3. Tier3 strong buy stocks not yet in watchlist

## Recommendations
1. Add Tier3 stocks to watchlist (2379, 2451, 2458, 2474, 2884, 3413, 6230, 8081)
2. Review/replace 00713 and 0056 with better alternatives
3. Run full backtest to update SignalLogs
