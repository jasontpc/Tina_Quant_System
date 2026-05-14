import yfinance as yf
import pandas as pd
from datetime import datetime
import sys

PORTFOLIO_VALUE = 745000
CASH_RESERVE = 1255000
TOTAL_ASSETS = PORTFOLIO_VALUE + CASH_RESERVE
TARGET_ALLOCATION = 0.40

positions = [
    {'symbol':'2376.TW','name':'技嘉','cost':301,'shares':664,'rsi_entry':45,'hold_days':5},
    {'symbol':'3034.TW','name':'緯穎','cost':442,'shares':336,'rsi_entry':50,'hold_days':5},
    {'symbol':'2379.TW','name':'環球晶','cost':543,'shares':367,'rsi_entry':55,'hold_days':5},
]
last_checks = {
    '2376.TW': {'price':321.0,'rsi':67.8,'kdj_J':95.7,'macd_hist':3.42,'ma5':301.0,'ma20':263.5,'ma60':228.0,'pnl_pct':6.6},
    '3034.TW': {'price':487.0,'rsi':71.6,'kdj_J':104.5,'macd_hist':7.97,'ma5':441.5,'ma20':398.5,'ma60':373.5,'pnl_pct':10.2},
    '2379.TW': {'price':555.0,'rsi':51.0,'kdj_J':53.4,'macd_hist':0.71,'ma5':544.0,'ma20':524.0,'ma60':487.0,'pnl_pct':2.2},
}

print("=" * 60)
print("  TINA 7-LAYER PORTFOLIO ANALYSIS  2026-05-12")
print("=" * 60)

# ─── LAYER 1: TARGET TRACKING ───
print("\n[Layer 1] TARGET TRACKING")
total_pos_value = sum(p['shares'] * last_checks[p['symbol']]['price'] for p in positions)
total_value = PORTFOLIO_VALUE
allocation_pct = total_pos_value / TOTAL_ASSETS * 100
print("  Total Portfolio Value:   %.0f" % total_pos_value)
print("  Cash Reserve:            %.0f" % CASH_RESERVE)
print("  Total Assets:            %.0f" % TOTAL_ASSETS)
print("  Current Allocation:     %.1f%%  (Target: %.0f%%)" % (allocation_pct, TARGET_ALLOCATION*100))
gaps = (TARGET_ALLOCATION * TOTAL_ASSETS - total_pos_value) / TOTAL_ASSETS * 100
print("  Gap to Target:          %+.1f%% cash idle" % gaps)
total_pnl = sum((last_checks[p['symbol']]['price'] - p['cost']) * p['shares'] for p in positions)
total_cost = sum(p['cost'] * p['shares'] for p in positions)
total_pnl_pct = total_pnl / total_cost * 100
print("  Total P&L:             %+.1f%%  (NT$ %d)" % (total_pnl_pct, total_pnl))

# ─── LAYER 2: RISK MANAGEMENT ───
print("\n[Layer 2] RISK MANAGEMENT")
twii = yf.download('^TWII', period='20d', interval='1d', auto_adjust=True, progress=False, timeout=10)
twii.columns = [c[0] for c in twii.columns] if isinstance(twii.columns, pd.MultiIndex) else twii.columns
close = twii['Close']
delta = close.diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
twii_rsi = float((100 - (100/(1+gain/loss))).iloc[-1])
twii_price = float(close.iloc[-1])

vix = yf.download('^VIX', period='1mo', interval='1d', auto_adjust=True, progress=False, timeout=10)
vix.columns = [c[0] for c in vix.columns] if isinstance(vix.columns, pd.MultiIndex) else vix.columns
vix_cur = float(vix['Close'].iloc[-1])
vix_ma20 = float(vix['Close'].rolling(20).mean().iloc[-1])
vix_ma5 = float(vix['Close'].rolling(5).mean().iloc[-1])

# TWII RSI tier
if twii_rsi > 90: twii_tier = 'EXTREME'; twii_action = 'EXIT ALL (90+)'
elif twii_rsi > 85: twii_tier = 'DANGER'; twii_action = '降50%部位'
elif twii_rsi > 80: twii_tier = 'HOT'; twii_action = '降25%部位'
elif twii_rsi > 75: twii_tier = 'WARM'; twii_action = '謹慎，不新倉'
else: twii_tier = 'NORMAL'; twii_action = '正常操作'

# VIX tier
if vix_cur < 15: vix_tier = 'LOW'; vix_regime = 'RISK-ON'
elif vix_cur < 20: vix_tier = 'MEDIUM'; vix_regime = 'TRANSITION'
elif vix_cur < 30: vix_tier = 'HIGH'; vix_regime = 'RISK-OFF'
else: vix_tier = 'EXTREME'; vix_regime = 'CRISIS'

print("  TWII RSI: %.1f  [%s] -> %s" % (twii_rsi, twii_tier, twii_action))
print("  VIX:      %.1f  [%s] -> %s" % (vix_cur, vix_tier, vix_regime))
print("  VIX vs MA20: %+.1f%%  (%s)" % ((vix_cur-vix_ma20)/vix_ma20*100, 'INFLATING' if vix_cur > vix_ma5 else 'DEFLATING'))

# Combined risk verdict
if twii_rsi > 85 or vix_cur > 30:
    risk_verdict = 'HIGH RISK'
elif twii_rsi > 80 or vix_cur > 20:
    risk_verdict = 'MODERATE RISK'
else:
    risk_verdict = 'LOW RISK'
print("  Combined Verdict:       [%s]" % risk_verdict)

# ─── LAYER 3: POSITION TIMER ───
print("\n[Layer 3] POSITION TIMER")
for p in positions:
    lc = last_checks[p['symbol']]
    price = lc['price']
    cost = p['cost']
    pnl = (price - cost) / cost * 100
    days = p['hold_days']
    stop_loss = cost * 0.92
    stop_distance = (price - stop_loss) / price * 100
    # Target: 10% or RSI>75
    target = cost * 1.10
    target_distance = (target - price) / price * 100
    print("  %-8s Cost:%6.0f  Price:%6.0f  %+6.1f%%  %ddays  Stop:%+.1f%%  Target:%+.1f%%" % (
        p['symbol'], cost, price, pnl, days, stop_distance, target_distance))
    # Timer alert
    if days > 15: print("    !! HOLDING %d DAYS - FORCE REDUCE HALF" % days)
    elif days > 10: print("    ! Setting MA5 trailing stop")

# ─── LAYER 4: MARKET CONTEXT ───
print("\n[Layer 4] MARKET CONTEXT")
spx = yf.download('^SPX', period='1mo', interval='1d', auto_adjust=True, progress=False, timeout=10)
spx.columns = [c[0] for c in spx.columns] if isinstance(spx.columns, pd.MultiIndex) else spx.columns
spx_ret_5d = float((spx['Close'].iloc[-1]/spx['Close'].iloc[-5]-1)*100)
spx_ret_20d = float((spx['Close'].iloc[-1]/spx['Close'].iloc[-20]-1)*100) if len(spx) >= 20 else None
ndx = yf.download('^NDX', period='5d', interval='1d', auto_adjust=True, progress=False, timeout=10)
ndx.columns = [c[0] for c in ndx.columns] if isinstance(ndx.columns, pd.MultiIndex) else ndx.columns
ndx_ret = float((ndx['Close'].iloc[-1]/ndx['Close'].iloc[-5]-1)*100)
print("  S&P500:  5D %+.1f%%  20D %+.1f%%" % (spx_ret_5d, spx_ret_20d))
print("  NASDAQ:  5D %+.1f%%" % ndx_ret)
xle = yf.download('XLE', period='5d', interval='1d', auto_adjust=True, progress=False, timeout=10)
xle.columns = [c[0] for c in xle.columns] if isinstance(xle.columns, pd.MultiIndex) else xle.columns
xlv = yf.download('XLV', period='5d', interval='1d', auto_adjust=True, progress=False, timeout=10)
xlv.columns = [c[0] for c in xlv.columns] if isinstance(xlv.columns, pd.MultiIndex) else xlv.columns
xle_ret = float((xle['Close'].iloc[-1]/xle['Close'].iloc[-2]-1)*100)
xlv_ret = float((xlv['Close'].iloc[-1]/xlv['Close'].iloc[-2]-1)*100)
spread = xle_ret - xlv_ret
print("  XLE vs XLV spread: %+.2f%%  [%s]" % (spread,
    'COMMODITY/INFLATION' if spread > 1 else 'DEFENSIVE/HEALTHCARE' if spread < -1 else 'NEUTRAL'))
print("  Market Signal:       [%s]" % ('BROAD RISK-ON' if spx_ret_5d > 1 and ndx_ret > 1 else
    'DEFENSIVE' if ndx_ret < -1 else 'ROTATION'))

# ─── LAYER 5: SECTOR CHECK ───
print("\n[Layer 5] SECTOR ROTATION CHECK")
sector_stocks = {'2376.TW':'Tech/Hardware','3034.TW':'AI/Server','2379.TW':'Semiconductor'}
sector_signal = {'Tech/Hardware':'WATCH','AI/Server':'CAUTION','Semiconductor':'BUY'}
for sym, sector in sector_stocks.items():
    lc = last_checks[sym]
    print("  %-8s -> %-20s  RSI:%5.1f  J:%5.1f  Signal:%s" % (
        sym, sector, lc['rsi'], lc['kdj_J'], sector_signal[sector]))

# ─── LAYER 6: TINA EXIT ENGINE v2 ───
print("\n[Layer 6] TINA EXIT ENGINE v2.0")
import exit_engine as ee
market = {'twii_rsi': twii_rsi}
pos_data = {'positions': [
    {'symbol':p['symbol'],'cost':p['cost'],'shares':p['shares'],'hold_days':p['hold_days'],
     'last_check': last_checks[p['symbol']]}
    for p in positions
]}
results = ee.score_all_positions(pos_data, market)
for r in results:
    ft = ' [FAST]' if r.get('fast_trigger') else ''
    sigs = ','.join(r['signals'])
    print("  %-8s  Score:%3d  %-12s%s" % (r['symbol'], r['total_score'], r['signal'], ft))
    print("    Triggers: %s" % sigs)

# ─── LAYER 7: FINAL ACTION ───
print("\n[Layer 7] FINAL ACTION RECOMMENDATION")

# Calculate composite score
exit_signals = {'EXIT_NOW':3,'EXIT_HALF':2,'WATCH':1,'HOLD':0}
scores = [exit_signals.get(r['signal'],0) for r in results]
avg_signal = sum(scores)/len(scores) if scores else 0
max_signal = max(scores) if scores else 0

# Overall regime verdict
if twii_rsi > 85 and vix_cur > 20:
    regime = 'HIGH CAUTION'
elif twii_rsi > 80 or vix_cur > 20:
    regime = 'ELEVATED'
elif twii_rsi > 75 or vix_cur > 15:
    regime = 'NEUTRAL'
else:
    regime = 'BULLISH'

print("  Regime:     [%s]" % regime)
print("  Avg Signal: %.1f/3  (0=HOLD, 3=EXIT ALL)" % avg_signal)
print("  Max Signal: %d/3" % max_signal)

# Specific recommendations per position
print("\n  POSITION RECOMMENDATIONS:")
for p in positions:
    lc = last_checks[p['symbol']]
    r = next((x for x in results if x['symbol'] == p['symbol']), None)
    sig = r['signal'] if r else 'HOLD'
    score = r['total_score'] if r else 0
    
    if sig == 'EXIT_NOW':
        action = 'EXIT FULL (now)'
    elif sig == 'EXIT_HALF':
        action = 'EXIT HALF, hold rest with trailing MA5 stop'
    elif sig == 'WATCH':
        if lc['kdj_J'] > 95:
            action = 'WATCH + set MA5 trailing stop (J>95)'
        else:
            action = 'HOLD, set MA20 trailing stop'
    else:
        action = 'HOLD'

    print("  %-8s [%s] Score:%3d -> %s" % (p['symbol'], sig, score, action))

# Cash deployment plan
print("\n  CASH RESERVE PLAN:")
idle_pct = CASH_RESERVE / TOTAL_ASSETS * 100
print("  Idle cash: %.0f (%.1f%% of total assets)" % (CASH_RESERVE, idle_pct))
if twii_rsi > 80:
    print("  Decision: STAY CASH - TWII RSI > 80, no new entries")
elif twii_rsi > 75:
    print("  Decision: STAY CASH - TWII RSI still elevated")
else:
    print("  Decision: WAIT FOR PULLBACK - monitor RSI < 75 entry window")

print("\n" + "=" * 60)
print("  GENERATED: %s" % datetime.now().strftime('%Y-%m-%d %H:%M'))
print("=" * 60)