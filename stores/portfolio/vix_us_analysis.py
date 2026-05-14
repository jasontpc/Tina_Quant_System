import yfinance as yf
import pandas as pd

print("=" * 60)
print("  US STOCK MARKET + VIX ANALYSIS  2026-05-12")
print("=" * 60)

indices = {
    '^SPX': 'S&P 500',
    '^NDX': 'NASDAQ 100',
    '^VIX': 'VIX',
    '^SOX': 'PHLX Semiconductor',
    'XLE': 'Energy Select',
    'XLK': 'Technology Select',
    'XLV': 'Healthcare Select',
    'XLF': 'Financial Select',
    'IWM': 'Russell 2000',
    'DXY': 'US Dollar Index',
    'GLD': 'Gold',
    'TLT': '20Y Treasury',
}

results = {}
for sym, name in indices.items():
    try:
        df = yf.download(sym, period='5d', interval='1d', auto_adjust=True, progress=False, timeout=10)
        if df.empty:
            results[name] = None
            continue
        df.columns = [c[0] for c in df.columns] if isinstance(df.columns, pd.MultiIndex) else df.columns
        close = float(df['Close'].iloc[-1])
        prev = float(df['Close'].iloc[-2])
        change = (close / prev - 1) * 100 if prev > 0 else 0
        results[name] = {'close': close, 'prev': prev, 'change': change}
    except:
        results[name] = None

vix = results.get('VIX', {})
vix_current = vix['close'] if vix else None
vix_change = vix['change'] if vix else None

print("\n[1] MAJOR INDICES")
for name, sym in [('S&P 500','^SPX'),('NASDAQ 100','^NDX'),('Russell 2000','IWM')]:
    d = results.get(name, {})
    if d:
        print("  %-25s %10.2f  %+6.2f%%" % (name, d['close'], d['change']))

print("\n[2] SECTORS & THEMATIC")
for name, sym in [('PHLX Semiconductor','^SOX'),('Technology Select','XLK'),
                  ('Healthcare Select','XLV'),('Financial Select','XLF'),('Energy Select','XLE')]:
    d = results.get(name, {})
    if d:
        print("  %-25s %10.2f  %+6.2f%%" % (name, d['close'], d['change']))

print("\n[3] VIX & FEAR GAUGE")
if vix:
    print("  VIX Current:           %.2f  (%+.1f%% today)" % (vix_current, vix_change))
    try:
        vix_1m = yf.download('^VIX', period='1mo', interval='1d', auto_adjust=True, progress=False, timeout=10)
        vix_1m.columns = [c[0] for c in vix_1m.columns] if isinstance(vix_1m.columns, pd.MultiIndex) else vix_1m.columns
        ma20 = vix_1m['Close'].rolling(20).mean().iloc[-1]
        ma5 = vix_1m['Close'].rolling(5).mean().iloc[-1]
        trend = 'INFLATING (+)' if vix_current > ma5 else 'DEFLATING (-)'
        print("  VIX MA20:              %.2f" % ma20)
        print("  VIX Trend:             %s" % trend)
        dev = (vix_current - ma20) / ma20 * 100
        print("  VIX vs MA20:           %+.1f%% deviation" % dev)
    except Exception as e:
        print("  VIX MA calcs failed: %s" % e)

print("\n[4] DOLLAR, BONDS & COMMODITIES")
for name in ['US Dollar Index','Gold','20Y Treasury']:
    d = results.get(name, {})
    if d:
        print("  %-25s %10.2f  %+6.2f%%" % (name, d['close'], d['change']))

print("\n[5] MARKET REGIME (VIX-Based)")
spx = results.get('S&P 500', {})
ndx = results.get('NASDAQ 100', {})
iwm = results.get('Russell 2000', {})

regime = ''
regime_desc = ''
regime_action = ''
if vix_current:
    if vix_current < 15:
        regime = 'RISK-ON'
        regime_desc = 'Low volatility - momentum + growth led'
        regime_action = 'BUY dips, add leverage, TQQQ/QLD style'
    elif vix_current < 20:
        regime = 'TRANSITION'
        regime_desc = 'Moderate volatility - rotation, profit-taking'
        regime_action = 'REDUCE leverage, shift to quality, take runner profits'
    elif vix_current < 30:
        regime = 'RISK-OFF'
        regime_desc = 'High volatility - flight to safety'
        regime_action = 'HIBERNATE: cash + SPXU/SDow, wait'
    else:
        regime = 'CRISIS'
        regime_desc = 'Extreme volatility - systemic panic'
        regime_action = 'SURVIVE: cash only, no catch knives'

print("  CURRENT REGIME:        [%s]" % regime)
print("  Description:          %s" % regime_desc)
print("  Recommended Action:    %s" % regime_action)

if ndx and spx:
    ndx_sp = ndx['close'] / spx['close']
    print("\n  NDX/SPX Ratio:         %.4f  (%s)" % (ndx_sp, 'Tech Leading' if ndx_sp > 0.38 else 'Broad'))

if iwm and spx:
    iwm_sp = iwm['close'] / spx['close']
    print("  IWM/SPX Ratio:         %.4f  (%s)" % (iwm_sp, 'Small Cap Leadership' if iwm_sp > 0.10 else 'Large Cap'))

print("\n[6] VIX HEDGE SIGNALS")
if vix_current:
    if vix_current < 15:
        print("  VIX < 15: Complacency - buy cheap hedges (SVIX or VIX calls)")
        print("  Buy: SVIX, small VIX call positions")
    elif vix_current < 20:
        print("  VIX 15-20: Normal - no specific hedge needed")
        print("  Maintain: stop losses, size appropriately")
    elif vix_current < 30:
        print("  VIX 20-30: Elevated - consider protective puts")
        print("  Hedge: SPY puts ATM or VIX call spreads")
    else:
        print("  VIX > 30: Extreme - maximum protection, no new longs")
        print("  Hedge: VIX calls directly, SPXL puts")

print("\n[7] SECTOR ROTATION CHECK")
xlk = results.get('Technology Select', {})
xlf = results.get('Financial Select', {})
xle = results.get('Energy Select', {})
if xlk and xlf:
    tech_vs_fin = xlk['change'] - xlf['change']
    print("  Tech vs Financial:    %+.2f%% spread" % tech_vs_fin)
    if tech_vs_fin > 1:
        print("  -> TECH LEADING: growth/momentum regime")
    elif tech_vs_fin < -1:
        print("  -> FINANCIALS LEADING: value/defensive regime")
    else:
        print("  -> MIXED: no clear sector leadership")

if xle and xlk:
    energy_vs_tech = xle['change'] - xlk['change']
    print("  Energy vs Tech:        %+.2f%% spread" % energy_vs_tech)
    if energy_vs_tech > 1:
        print("  -> ENERGY LEADING: commodity/inflation regime")
    else:
        print("  -> NON-COMMODITY: no inflation signal")

print("\n" + "=" * 60)
if vix_current:
    print("  SUMMARY: VIX=%.0f  REGIME=[%s]" % (vix_current, regime))
print("=" * 60)