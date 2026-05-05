import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# US stocks under 100
us_stocks = [
    ('DLO', 'Deloitte', 13.75),
    ('GEN', 'Gen', 19.37),
    ('RIVN', 'Rivian', 15.02),
    ('DXCM', 'DexCom', 61.35),
    ('SOFI', 'SoFi', 8.92),
    ('BILL', 'Bill.com', 45.23),
    ('GTLB', 'Gitlab', 55.12),
    ('PATH', 'UiPath', 23.45),
    ('ESTC', 'Elastic', 78.90),
    ('COIN', 'Coinbase', 172.50),
    ('SMCI', 'SuperMicro', 360.54),
    ('U', 'Unity', 22.15),
    ('RKLB', 'RocketLab', 78.81),
    ('D', 'Dominion', 51.23),
    ('BMY', 'Bristol-Myers', 52.45),
    ('SO', 'Southern Company', 72.30),
]

# TW stocks under 200
tw_stocks = [
    ('2881', 'Fubon Fin', 90.0),
    ('2884', 'E.Sun', 31.85),
    ('2891', 'CTBC', 52.30),
    ('2883', 'Devt Cu', 21.50),
    ('2886', 'Mega', 39.10),
    ('2855', 'Uni Pres', 35.60),
    ('2330', 'TSMC', 2135.0),
    ('2382', 'Quanta', 312.50),
    ('2454', 'MediaTek', 2610.0),
    ('3231', 'Wistron', 137.0),
    ('4961', 'eMemory', 152.5),
    ('2345', 'Elan', 2280.0),
]

def score_stock(rsi, price, ma20, rev_g, pe, ret_3m):
    s = 0
    if 35 <= rsi <= 65: s += 3
    elif rsi < 35: s += 2
    if price > ma20: s += 1
    if rev_g > 0.2: s += 2
    if pe > 0 and pe < 25: s += 2
    if ret_3m > 0: s += 1
    return s

print('=== US VALUE GROWTH STOCKS (Under 100) ===')
results_us = []
for ticker, name, price in us_stocks:
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period='6mo')
        info = tk.info
        if len(h) < 20:
            continue
        
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        rev_g = info.get('revenueGrowth', 0) or 0
        pe = info.get('trailingPE', 0) or 0
        ret_3m = (price / float(h['Close'].iloc[-60]) - 1) * 100 if len(h) >= 60 else (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        
        score = score_stock(rsi, price, ma20, rev_g, pe, ret_3m)
        
        results_us.append({
            'ticker': ticker, 'name': name, 'price': price,
            'rsi': rsi, 'rev_g': rev_g, 'pe': pe, 'ret_3m': ret_3m,
            'score': score, 'above_ma20': price > ma20
        })
    except Exception as e:
        print('Error:', ticker, str(e))

results_us.sort(key=lambda x: x['score'], reverse=True)

print('Ticker  Name              Price    RSI   RevGrowth   PE     3M     Score')
print('-'*75)
for r in results_us[:12]:
    pe_s = str(round(r['pe'])) if r['pe'] > 0 else 'N/A'
    rev_s = str(round(r['rev_g']*100)) + '%'
    print(f"{r['ticker']:<8} {r['name']:<16} {r['price']:>7.2f} {r['rsi']:>5.1f} {rev_s:>10} {pe_s:>6} {r['ret_3m']:>6.1f} {r['score']}")

print()
print('=== TW VALUE GROWTH STOCKS (Under 200) ===')
results_tw = []
for ticker, name, price in tw_stocks:
    try:
        tk = yf.Ticker(ticker + '.TW')
        h = tk.history(period='6mo')
        info = tk.info
        if len(h) < 20:
            continue
        
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        rev_g = info.get('revenueGrowth', 0) or 0
        pe = info.get('trailingPE', 0) or 0
        ret_3m = (price / float(h['Close'].iloc[-60]) - 1) * 100 if len(h) >= 60 else (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        
        score = score_stock(rsi, price, ma20, rev_g, pe, ret_3m)
        
        results_tw.append({
            'ticker': ticker, 'name': name, 'price': price,
            'rsi': rsi, 'rev_g': rev_g, 'pe': pe, 'ret_3m': ret_3m,
            'score': score, 'above_ma20': price > ma20
        })
    except Exception as e:
        print('Error:', ticker, str(e))

results_tw.sort(key=lambda x: x['score'], reverse=True)

print('Ticker  Name              Price    RSI   RevGrowth   PE     3M     Score')
print('-'*75)
for r in results_tw[:12]:
    pe_s = str(round(r['pe'])) if r['pe'] > 0 else 'N/A'
    rev_s = str(round(r['rev_g']*100)) + '%'
    print(f"{r['ticker']:<8} {r['name']:<16} {r['price']:>7.2f} {r['rsi']:>5.1f} {rev_s:>10} {pe_s:>6} {r['ret_3m']:>6.1f} {r['score']}")

print()
print('='*75)
print('TOP PICKS')
print('='*75)
print('\n[US TOP 3]')
for r in results_us[:3]:
    action = 'BUY' if 35 <= r['rsi'] <= 65 and r['score'] >= 7 else 'WATCH'
    print(f"  {r['ticker']} {r['name']}: ${r['price']} RSI={r['rsi']:.1f} Rev={r['rev_g']*100:.0f}% Score={r['score']} [{action}]")

print('\n[TW TOP 3]')
for r in results_tw[:3]:
    action = 'BUY' if 35 <= r['rsi'] <= 65 and r['score'] >= 7 else 'WATCH'
    print(f"  {r['ticker']} {r['name']}: ${r['price']} RSI={r['rsi']:.1f} Rev={r['rev_g']*100:.0f}% Score={r['score']} [{action}]")