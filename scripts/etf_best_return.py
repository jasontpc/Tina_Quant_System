import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

etfs = [
    ('0050', 'Yuan Taiwn 50', 'TW'),
    ('0056', 'Yuan High Div', 'TW'),
    ('00713', 'Yuan High Yield Low Vol', 'TW'),
    ('00646', 'Fubon S&P500', 'TW'),
    ('VEA', 'Vanguard Dev Markets', 'US'),
    ('BND', 'BND Total Bond', 'US'),
    ('VTI', 'Vanguard All Market', 'US'),
    ('QQQ', 'Nasdaq 100', 'US'),
    ('VOO', 'Vanguard S&P500', 'US'),
]

print('ETF ANALYSIS FOR HIGHEST RETURN STRATEGY')
print('='*70)

results = []
for ticker, name, market in etfs:
    try:
        sym = ticker + '.TW' if market == 'TW' else ticker
        tk = yf.Ticker(sym)
        h = tk.history(period='6mo')
        if len(h) < 30:
            continue
        
        price = float(h['Close'].iloc[-1])
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        ret_3m = (price / float(h['Close'].iloc[-60]) - 1) * 100 if len(h) >= 60 else 0
        ret_6m = (price / float(h['Close'].iloc[-120]) - 1) * 100 if len(h) >= 120 else 0
        
        above_ma20 = price > ma20
        
        # Score for entry timing
        score = 0
        if rsi < 40:
            score = 10  # Undervalued
        elif rsi < 55:
            score = 8   # Good value
        elif rsi < 65:
            score = 5   # Fair
        elif rsi < 75:
            score = 2   # Overvalued
        else:
            score = 0   # Extremely overvalued
        
        if above_ma20:
            score += 2
        
        results.append({
            'ticker': ticker, 'name': name, 'market': market,
            'price': price, 'rsi': rsi, 'ret_1m': ret_1m, 'ret_3m': ret_3m, 'ret_6m': ret_6m,
            'above_ma20': above_ma20, 'score': score
        })
    except Exception as e:
        print('Error:', ticker, str(e))

results.sort(key=lambda x: x['score'], reverse=True)

print('Ticker  Name             Price      RSI    1M    3M    6M   MA20  Score')
print('-'*75)
for r in results:
    ma = 'ABOVE' if r['above_ma20'] else 'BELOW'
    print(f"{r['ticker']:<8} {r['name']:<15} {r['price']:>9.2f} {r['rsi']:>5.1f} {r['ret_1m']:>6.1f} {r['ret_3m']:>6.1f} {r['ret_6m']:>6.1f} {ma:<6} {r['score']}")

print()
print('='*70)
print('RECOMMENDATIONS')
print('='*70)

print('\n[NOW ENTRY - HIGH SCORE]')
for r in results[:3]:
    if r['score'] >= 7:
        action = 'BUY NOW' if r['score'] >= 9 else 'Consider entry'
        print(f"  {r['ticker']} {r['name']}: RSI {r['rsi']:.1f}, Score {r['score']} - {action}")

print('\n[WAIT - MEDIUM SCORE]')
for r in results[3:6]:
    if r['score'] >= 5:
        print(f"  {r['ticker']} {r['name']}: RSI {r['rsi']:.1f}, Score {r['score']} - Wait for RSI < 55 or MA20 breakout")

print('\n[AVOID - LOW SCORE]')
for r in results:
    if r['score'] < 5:
        print(f"  {r['ticker']} {r['name']}: RSI {r['rsi']:.1f} - OVERHEATED, do not buy")

print('\n' + '='*70)
print('HIGHEST RETURN STRATEGY')
print('='*70)
print('\nBased on current data, ranked by entry timing score:')
for i, r in enumerate(results[:5], 1):
    print(f"  {i}. {r['ticker']} ({r['market']}): Score {r['score']} - RSI {r['rsi']:.1f}, 6M return {r['ret_6m']:.1f}%")