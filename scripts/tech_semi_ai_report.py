import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Tech/Semi/AI stocks
stocks = [
    # Taiwan Semi/Tech
    ('2330', 'TSMC', 'TW'),
    ('2454', 'MediaTek', 'TW'),
    ('2317', 'Foxconn', 'TW'),
    ('2382', 'Quanta', 'TW'),
    ('3034', 'Wiwynn', 'TW'),
    ('3665', 'WinWay', 'TW'),
    ('4961', 'eMemory', 'TW'),
    ('2345', 'Accton', 'TW'),
    ('3037', 'Unimicron', 'TW'),
    ('2458', 'Elan', 'TW'),
    ('3017', 'AVC', 'TW'),
    ('3231', 'Wistron', 'TW'),
    # US Tech/AI/Semi
    ('NVDA', 'Nvidia', 'US'),
    ('AMD', 'AMD', 'US'),
    ('INTC', 'Intel', 'US'),
    ('TSM', 'TSMC ADR', 'US'),
    ('SMCI', 'SuperMicro', 'US'),
    ('COIN', 'Coinbase', 'US'),
    ('PATH', 'UiPath', 'US'),
    ('U', 'Unity', 'US'),
    ('RIVN', 'Rivian', 'US'),
    ('RKLB', 'RocketLab', 'US'),
]

results = []
for ticker, name, market in stocks:
    try:
        sym = ticker + '.TW' if market == 'TW' else ticker
        tk = yf.Ticker(sym)
        h = tk.history(period='3mo')
        info = tk.info
        if len(h) < 20:
            continue
        
        price = float(h['Close'].iloc[-1])
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        ma60 = float(h['Close'].rolling(60).mean().iloc[-1]) if len(h) >= 60 else None
        rev_g = info.get('revenueGrowth', 0) or 0
        pe = info.get('trailingPE', 0) or 0
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        ret_3m = (price / float(h['Close'].iloc[-60]) - 1) * 100 if len(h) >= 60 else 0
        
        score = 0
        if 35 <= rsi <= 65: score += 3
        elif rsi < 35: score += 2
        if price > ma20: score += 2
        if ma60 and price > ma60: score += 1
        if rev_g > 0.2: score += 2
        if pe > 0 and pe < 30: score += 1
        
        results.append({
            'ticker': ticker, 'name': name, 'market': market,
            'price': price, 'rsi': rsi, 'ma20': ma20, 'ma60': ma60,
            'rev_g': rev_g, 'pe': pe, 'ret_1m': ret_1m, 'ret_3m': ret_3m,
            'score': score, 'above_ma20': price > ma20, 'above_ma60': ma60 and price > ma60
        })
    except Exception as e:
        print('Error:', ticker, str(e)[:40])

results.sort(key=lambda x: x['score'], reverse=True)

print('TECH/SEMI/AI STOCKS REPORT')
print('='*80)
print('Code     Name           Mkt   Price      RSI    1M      3M      Rev     PE   Score')
print('-'*80)
for r in results:
    pe_s = str(round(r['pe'])) if r['pe'] > 0 else 'N/A'
    rev_s = str(round(r['rev_g']*100)) + '%'
    print(f"{r['ticker']:<8} {r['name']:<13} {r['market']:<4} {r['price']:>9.2f} {r['rsi']:>6.1f} {r['ret_1m']:>7.1f} {r['ret_3m']:>7.1f} {rev_s:>7} {pe_s:>5} {r['score']}")

print()
print('='*80)
print('TOP PICKS BY SCORE')
print('='*80)
for r in results[:8]:
    zone = 'BUY' if 35 <= r['rsi'] <= 65 else 'WATCH' if r['rsi'] < 70 else 'HOT'
    print(f"  {r['ticker']} {r['name']}: ${r['price']:.2f} RSI={r['rsi']:.1f} Score={r['score']} [{zone}]")

print()
print('='*80)
print('SECTORS')
print('='*80)
tw = [r for r in results if r['market'] == 'TW']
us = [r for r in results if r['market'] == 'US']
print('\n[Taiwan]')
for r in tw[:5]:
    print(f"  {r['ticker']} {r['name']}: RSI={r['rsi']:.1f} Rev={r['rev_g']*100:.0f}%")
print('\n[US]')
for r in us[:5]:
    print(f"  {r['ticker']} {r['name']}: RSI={r['rsi']:.1f} Rev={r['rev_g']*100:.0f}%")