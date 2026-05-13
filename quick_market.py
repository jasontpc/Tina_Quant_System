# -*- coding: utf-8 -*-
import yfinance as yf, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

symbols = {
    'TWII': '^TWII', 'SPX': '^GSPC', 'NDX': '^IXIC',
    'VIX': '^VIX', 'WTI': 'CL=F', 'TNX': '^TNX', 'DXY': 'DXY'
}

print('=== 12:13 即時行情 ===')
results = {}
for name, sym in symbols.items():
    try:
        h = yf.Ticker(sym).history(period='5d')
        if len(h) >= 2:
            cur = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            chg = (cur - prev) / prev * 100
            results[name] = {'price': round(cur, 2), 'change': round(chg, 2)}
    except:
        pass

for name, d in sorted(results.items()):
    arrow = '+' if d['change'] >= 0 else ''
    vol = ''
    print(f'{name:4}: {d["price"]:>10.2f}  {arrow}{d["change"]:>6.2f}%')

print()
# TWII RSI
try:
    twii = yf.Ticker('^TWII').history(period='90d', interval='1d')
    delta = twii['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    twii_rsi = rsi.iloc[-1]
    prev_rsi = rsi.iloc[-2]
    print(f'TWII RSI(14): {twii_rsi:.1f} (prev: {prev_rsi:.1f})')
except Exception as e:
    print(f'TWII RSI: N/A ({e})')

# SPX RSI
try:
    spx = yf.Ticker('^GSPC').history(period='90d', interval='1d')
    delta = spx['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    spx_rsi = rsi.iloc[-1]
    print(f'SPX RSI(14):  {spx_rsi:.1f}')
except:
    print('SPX RSI: N/A')

# NVDA price
try:
    nvda = yf.Ticker('NVDA').history(period='5d')
    cur = nvda['Close'].iloc[-1]
    prev = nvda['Close'].iloc[-2]
    chg = (cur - prev) / prev * 100
    arrow = '+' if chg >= 0 else ''
    print(f'NVDA:     {cur:>10.2f}  {arrow}{chg:>6.2f}%')
except:
    print('NVDA: N/A')