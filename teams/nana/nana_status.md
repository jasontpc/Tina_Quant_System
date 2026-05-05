# Nana Status | 2026-04-26 06:00 GMT+8

## System Health
- autonomous_trader.py: ✅ OK (7 pre-fix trades, WR=28.6%, Avg=-0.28%)
- trade_predictor.py: ✅ OK (10 stocks, 0 opps, 7 HIGH risk)
- market_regime.json: ⚠️ OVERBOUGHT (TWII RSI=83.7, rapidly escalating from 76.6)
- tier databases: ⚠️ tier1/2/3 synced but return_pct=0 (sync issue)

## Market Status
- Regime: **OVERBOUGHT** 🔴 (TWII RSI=83.7, RSI jumped 76.6→83.7 in ~25min)
- TWII close: ~22,714 (yesterday)
- Open positions: **0** (all cleared, all pre-fix bad trades)
- **No new entries blocked until RSI<70**
- entry_RSI_max=60 (OVERBOUGHT override)

## Scan Results (06:00)
- 10 stocks scanned | 0 opportunities | 7 HIGH risk
- 3665 穎崴 RSI=93.4, 3017 奇鋐 RSI=86.6, 2317 鴻海 RSI=82.0
- Best watch: 2886 兆豐金 RSI=54.3 (NEUTRAL, lowest risk)

## v5.39 Production Stats
- Config: BH=5.0, ATR=3.5x, MH=7d, RSI=40-65, Bias=-5 to 8, Score≥25
- Total=255 trades | WR=74.9% | Avg=3.55%
- BIAS_EXIT: WR=97.4%, Avg=6.54% (153 trades, best exit trigger)

## Known Issues
1. 🔴 MA120 NaN - period='3mo' insufficient, needs '1y'
2. 🟡 00919 delisted - needs 2020-2021 filter
3. 🟡 tier DB sync - return_pct=0
4. 🟡 autonomous_trades.json - 7 pre-fix trades need archival

## Entry Gate Status
- **🔴 LOCKED** (OVERBOUGHT regime, RSI=83.7 >> 70 threshold)
- Unlock condition: TWII RSI < 70
