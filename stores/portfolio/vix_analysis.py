import yfinance as yf
import pandas as pd
from datetime import datetime

print("=" * 55)
print("  VIX Analysis  2026-05-12")
print("=" * 55)

# 1. VIX
vix = yf.download('^VIX', period='5d', interval='1d', auto_adjust=True, progress=False)
if vix.empty:
    print("VIX fetch failed")
    exit()
vix.columns = [c[0] for c in vix.columns] if isinstance(vix.columns, pd.MultiIndex) else vix.columns
current = float(vix['Close'].iloc[-1])
high_5d = float(vix['High'].iloc[-1])
low_5d = float(vix['Low'].iloc[-1])
prev = float(vix['Close'].iloc[-2])

print(f"\n[1] VIX Current ({vix.index[-1].strftime('%Y-%m-%d')})")
print(f"  Current:  {current:.2f}")
print(f"  5D High:  {high_5d:.2f} | Low: {low_5d:.2f}")
print(f"  Change:   {current - prev:+.2f} ({(current/prev-1)*100:+.1f}%)")

# 2. VIX MA
vix_1m = yf.download('^VIX', period='1mo', interval='1d', auto_adjust=True, progress=False)
vix_1m.columns = [c[0] for c in vix_1m.columns] if isinstance(vix_1m.columns, pd.MultiIndex) else vix_1m.columns
close = vix_1m['Close']
ma5 = close.rolling(5).mean().iloc[-1]
ma10 = close.rolling(10).mean().iloc[-1]
ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None

print(f"\n[2] VIX Moving Averages")
print(f"  MA5:  {ma5:.2f}  {'ABOVE' if current > ma5 else 'BELOW'} (VIX premium: {'expensive' if current > ma5 else 'cheap'})")
print(f"  MA10: {ma10:.2f}  {'ABOVE' if current > ma10 else 'BELOW'}")
if ma20:
    print(f"  MA20: {ma20:.2f}  {'ABOVE' if current > ma20 else 'BELOW'}")
    dist_ma20 = (current - ma20) / ma20 * 100
    print(f"  Deviation from MA20: {dist_ma20:+.1f}%")

# 3. Tier
print(f"\n[3] VIX Tier & Implications")
tier_label = ''
tier_action = ''
tier_level = 0
bands = [(13,'LOW-NORMAL (Low volatility)','Risk-on: momentum trades, add positions'),
         (18,'MODERATE (Normal volatility)','Risk-on: trend following, hold core'),
         (25,'ELEVATED (Elevated caution)','REDUCE: reduce leverage, prepare hedges'),
         (35,'HIGH (Fear rising)','HIBERNATE: cash + inverse ETF'),
         (45,'EXTREME (Panic territory)','REVERSE: greed at bottom, accumulate quality')]
for level, label, action in bands:
    if current <= level:
        tier_label = label
        tier_action = action
        tier_level = level
        break

print(f"  VIX={current:.0f} -> [{tier_label}]")
print(f"  Action: {tier_action}")
print(f"  Within: {tier_level} tier")

# 4. Structure
print(f"\n[4] VIX Structure")
if ma5 > ma10:
    print(f"  Short structure: BULLISH (MA5 > MA10) -> volatility INFLATING")
else:
    print(f"  Short structure: BEARISH (MA5 < MA10) -> volatility DEFLATING")

# 5. Market context
print(f"\n[5] Market Context")
try:
    sp500 = yf.download('^SPX', period='20d', interval='1d', auto_adjust=True, progress=False)
    sp500.columns = [c[0] for c in sp500.columns] if isinstance(sp500.columns, pd.MultiIndex) else sp500.columns
    if len(sp500) >= 5:
        sp_ret_5d = (sp500['Close'].iloc[-1] / sp500['Close'].iloc[-5] - 1) * 100
        sp_ret_20d = (sp500['Close'].iloc[-1] / sp500['Close'].iloc[-20] - 1) * 100 if len(sp500) >= 20 else None
        print(f"  S&P500 5D return: {sp_ret_5d:+.1f}%")
        if sp_ret_20d:
            print(f"  S&P500 20D return: {sp_ret_20d:+.1f}%")
        if current > 25 and sp_ret_5d < 0:
            print(f"  -> RISK-OFF: VIX>25 + stocks down -> reduce exposure")
        elif current < 18 and sp_ret_5d > 0:
            print(f"  -> RISK-ON: VIX low + stocks up -> trend following OK")
        else:
            print(f"  -> MIXED: VIX={current:.0f}, S&P 5D={sp_ret_5d:+.1f}% -> neutral")
except Exception as e:
    print(f"  S&P500 context failed: {e}")

# 6. Rate context
print(f"\n[6] Fear Premium (VIX - Risk-Free Rate)")
try:
    irx = yf.download('^IRX', period='5d', progress=False)
    irx.columns = [c[0] for c in irx.columns] if isinstance(irx.columns, pd.MultiIndex) else irx.columns
    rf = float(irx['Close'].iloc[-1])
    premium = current - rf
    print(f"  13W Treasury yield (RF): {rf:.2f}%")
    print(f"  VIX - RF fear premium:    {premium:+.2f}%")
    if premium > 15:
        print(f"  -> FEAR PREMIUM > 15%: Panic, market paying high hedge cost")
    elif premium > 8:
        print(f"  -> FEAR PREMIUM 8-15%: Elevated fear, selective hedging")
    elif premium > 3:
        print(f"  -> FEAR PREMIUM 3-8%: Mild fear, normal behavior")
    else:
        print(f"  -> FEAR PREMIUM < 3%: Complacent, no fear premium")
except Exception as e:
    print(f"  Rate context failed: {e}")

print(f"\n{'=' * 55}")
print(f"  SUMMARY: VIX={current:.0f} -> {tier_label}")
print(f"  Direction: {tier_action}")
print(f"{'=' * 55}")