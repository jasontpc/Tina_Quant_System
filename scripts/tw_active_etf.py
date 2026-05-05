import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Taiwan active ETFs
etfs = [
    ('00929', 'Cathay Div Active', 21.50),
    ('00931B', 'FN-Day50', 18.20),
    ('00933B', 'FSITREND', 15.80),
    ('00770', 'Yuan Smart Med', 32.50),
    ('00701', 'Delt Shares', 24.30),
    ('00881', 'Innotech', 21.90),
    ('00891', 'AI Medical', 17.40),
    ('00905', 'Tech Select', 19.80),
    ('00915', 'Taiwan High Div', 23.60),
    ('00918', 'DLS Fin', 20.10),
]

print('=== TW ACTIVE ETFs ===')
results = []

for ticker, name, price in etfs:
    try:
        tk = yf.Ticker(ticker + '.TW')
        h = tk.history(period='3mo')
        info = tk.info
        if len(h) < 20:
            continue
        
        price = float(h['Close'].iloc[-1])
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        
        above_ma20 = price > ma20
        
        # Score
        score = 0
        if 35 <= rsi <= 65: score += 3
        elif rsi < 35: score += 2
        if above_ma20: score += 2
        if ret_1m > 3: score += 1
        if rsi > 75: score = max(0, score - 3)
        
        results.append({
            'ticker': ticker, 'name': name, 'price': price,
            'rsi': rsi, 'ret_1m': ret_1m, 'above_ma20': above_ma20, 'score': score
        })
    except Exception as e:
        print('Error:', ticker, str(e))

results.sort(key=lambda x: x['score'], reverse=True)

print('Ticker  Name               Price    RSI    1M    MA20   Score')
print('-'*65)
for r in results:
    ma = 'ABOVE' if r['above_ma20'] else 'BELOW'
    print(f"{r['ticker']:<8} {r['name']:<17} {r['price']:>7.2f} {r['rsi']:>6.1f} {r['ret_1m']:>6.1f} {ma:<6} {r['score']}")

print()
print('='*65)
print('RECOMMENDATIONS')
print('='*65)

buy = [r for r in results if r['score'] >= 5 and 35 <= r['rsi'] <= 65]
watch = [r for r in results if r['score'] >= 3 and r['rsi'] < 70]
avoid = [r for r in results if r['rsi'] > 70 or r['score'] < 3]

print('\n[BUY NOW]')
for r in buy:
    print(f"  {r['ticker']} {r['name']}: RSI {r['rsi']:.1f} 1M {r['ret_1m']:.1f}%")

print('\n[WATCH]')
for r in watch:
    print(f"  {r['ticker']} {r['name']}: RSI {r['rsi']:.1f}")

print('\n[AVOID]')
for r in avoid:
    print(f"  {r['ticker']} {r['name']}: RSI {r['rsi']:.1f} - OVERHEATED")