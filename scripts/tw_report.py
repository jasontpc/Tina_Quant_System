import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

print('='*60)
print('TW MARKET SENTIMENT')
print('='*60)

tk = yf.Ticker('^TWII')
h = tk.history(period='1mo')
if len(h) > 0:
    price = float(h['Close'].iloc[-1])
    rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
    ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
    ma60 = float(h['Close'].rolling(60).mean().iloc[-1]) if len(h) >= 60 else ma20
    ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
    
    above_ma20 = price > ma20
    above_ma60 = price > ma60
    
    print(f'加權指數: {price:.2f}')
    print(f'RSI(14): {rsi:.1f}')
    print(f'MA20: {ma20:.2f} ({"above" if above_ma20 else "below"})')
    print(f'MA60: {ma60:.2f} ({"above" if above_ma60 else "below"})')
    print(f'近1月報酬: {ret_1m:+.1f}%')
    
    if rsi > 75:
        status = 'OVERHEATED'
    elif rsi > 60:
        status = 'BULLISH'
    elif rsi < 40:
        status = 'OVERSOLD'
    else:
        status = 'NEUTRAL'
    
    print(f'Market Status: {status}')

print()
print('STOCK SCAN (Top Picks)')
print('-'*60)

tw_stocks = [
    ('2330', '2330.TW', 'TSMC'),
    ('2382', '2382.TW', 'Quanta'),
    ('3231', '3231.TW', 'Wistron'),
    ('2881', '2881.TW', 'Fubon'),
    ('2883', '2883.TW', 'KGI'),
    ('2884', '2884.TW', 'ESun'),
    ('2891', '2891.TW', 'CTBC'),
    ('2317', '2317.TW', 'Foxconn'),
    ('2454', '2454.TW', 'Mediatek'),
    ('3034', '3034.TW', 'Wiwynn'),
]

results = []
for code, ticker, name in tw_stocks:
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period='3mo')
        if len(h) < 30:
            continue
        
        price = float(h['Close'].iloc[-1])
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        
        above_ma20 = price > ma20
        ret_3m = (price / float(h['Close'].iloc[-60]) - 1) * 100 if len(h) >= 60 else 0
        
        results.append({
            'code': code,
            'name': name,
            'price': price,
            'rsi': rsi,
            'above_ma20': above_ma20,
            'ret_3m': ret_3m
        })
    except:
        pass

results.sort(key=lambda x: x['rsi'])

for r in results:
    ma20_s = '↑' if r['above_ma20'] else '↓'
    rsi_flag = ''
    if r['rsi'] > 75:
        rsi_flag = '*'
    elif r['rsi'] < 40:
        rsi_flag = '+'
    print(f"{r['code']} {r['name']:<8} {r['price']:>7.2f} RSI={r['rsi']:>5.1f}{rsi_flag} MA20={ma20_s} 3M={r['ret_3m']:>6.1f}%")

print()
print('* RSI > 75 OVERHEATED | + RSI < 40 OVERSOLD')