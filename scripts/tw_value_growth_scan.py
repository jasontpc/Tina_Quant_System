import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# TW stocks under 100
tw_stocks = [
    ('2881', 'Fubon Fin', 90.0),
    ('2883', 'KGI Fin', 21.5),
    ('2884', 'E.Sun', 31.85),
    ('2886', 'Mega Fin', 39.1),
    ('2891', 'CTBC', 52.3),
    ('2855', 'Uni Pres', 35.6),
    ('3717', 'Global', 19.5),
    ('2345', 'Accton', 2280.0),
    ('2303', 'UMC', 77.3),
    ('2458', 'Elan', 136.5),
    ('4961', 'eMemory', 152.5),
]

def score_stock(rsi, price, ma20, rev_g, pe, ret_3m):
    s = 0
    if 35 <= rsi <= 65: s += 3
    elif rsi < 35: s += 2
    if price > ma20: s += 1
    if rev_g > 0.2: s += 2
    if pe > 0 and pe < 20: s += 2
    if ret_3m > 0: s += 1
    return s

results = []
for ticker, name, price in tw_stocks:
    try:
        tk = yf.Ticker(ticker + '.TW')
        h = tk.history(period='6mo')
        info = tk.info
        if len(h) < 20:
            continue
        
        price_now = float(h['Close'].iloc[-1])
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        rev_g = info.get('revenueGrowth', 0) or 0
        pe = info.get('trailingPE', 0) or 0
        ret_3m = (price_now / float(h['Close'].iloc[-60]) - 1) * 100 if len(h) >= 60 else 0
        
        score = score_stock(rsi, price_now, ma20, rev_g, pe, ret_3m)
        
        results.append({
            'ticker': ticker, 'name': name, 'price': price_now,
            'rsi': rsi, 'rev_g': rev_g, 'pe': pe, 'ret_3m': ret_3m,
            'score': score, 'above_ma20': price_now > ma20
        })
    except Exception as e:
        print('Error:', ticker, str(e)[:50])

results.sort(key=lambda x: x['score'], reverse=True)

print('TW VALUE GROWTH STOCKS (Under 100)')
print('='*70)
print('Code     Name           Price    RSI   RevGrowth   PE     3M     Score')
print('-'*70)
for r in results:
    pe_s = str(round(r['pe'])) if r['pe'] > 0 else 'N/A'
    rev_s = str(round(r['rev_g']*100)) + '%'
    print(f"{r['ticker']:<8} {r['name']:<13} {r['price']:>8.2f} {r['rsi']:>6.1f} {rev_s:>10} {pe_s:>6} {r['ret_3m']:>7.1f} {r['score']}")

print()
print('TOP PICKS')
print('='*70)
buy = [r for r in results if r['score'] >= 7 and 35 <= r['rsi'] <= 65]
for r in buy[:5]:
    action = 'BUY' if r['score'] >= 8 else 'CONSIDER'
    print(f"  {r['ticker']} {r['name']}: {r['price']:.2f} RSI={r['rsi']:.1f} Rev={r['rev_g']*100:.0f}% Score={r['score']} [{action}]")