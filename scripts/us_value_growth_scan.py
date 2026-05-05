import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

us = [('DLO',13.75),('GEN',19.37),('RIVN',15.02),('SOFI',8.92),('BILL',45.23),('GTLB',55.12),('PATH',23.45),('U',27.13),('RKLB',78.81),('DXCM',61.35)]

results = []
for ticker, price in us:
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period='6mo')
        info = tk.info
        if len(h) < 20:
            continue
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        rev_g = info.get('revenueGrowth', 0) or 0
        pe = info.get('trailingPE', 0) or 0
        ret_3m = (float(h['Close'].iloc[-1]) / float(h['Close'].iloc[-60]) - 1) * 100 if len(h) >= 60 else 0
        score = 0
        if 35 <= rsi <= 65:
            score += 3
        elif rsi < 35:
            score += 2
        if rev_g > 0.2:
            score += 2
        if pe > 0 and pe < 25:
            score += 2
        if ret_3m > 0:
            score += 1
        results.append({'ticker': ticker, 'price': float(h['Close'].iloc[-1]), 'rsi': rsi, 'rev_g': rev_g, 'pe': pe, 'ret_3m': ret_3m, 'score': score})
    except:
        pass

results.sort(key=lambda x: x['score'], reverse=True)

print('US VALUE GROWTH STOCKS (Under 100)')
print('='*65)
for r in results[:8]:
    pe_s = str(round(r['pe'])) if r['pe'] > 0 else 'N/A'
    print(f"{r['ticker']:<8} {r['price']:>7.2f} RSI={r['rsi']:>5.1f} Rev={r['rev_g']*100:>5.0f}% PE={pe_s:>4} 3M={r['ret_3m']:>6.1f} Score={r['score']}")