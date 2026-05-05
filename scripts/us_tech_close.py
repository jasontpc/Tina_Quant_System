import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

stocks = [
    ('NVDA', 'Nvidia'),
    ('AMD', 'AMD'),
    ('INTC', 'Intel'),
    ('TSM', 'Taiwan Semi'),
    ('SMCI', 'Super Micro'),
    ('COIN', 'Coinbase'),
    ('SOFI', 'SoFi'),
    ('PATH', 'UiPath'),
    ('U', 'Unity Software'),
    ('BILL', 'Bill.com'),
    ('NET', 'Cloudflare'),
    ('GTLB', 'GitLab'),
    ('ESTC', 'Elastic'),
    ('DLO', 'Deloitte'),
    ('GEN', 'Gen'),
    ('RIVN', 'Rivian'),
    ('DXCM', 'DexCom'),
    ('RKLB', 'RocketLab'),
]

print('US Tech/Semi/AI 收盤分析')
print('=' * 70)

results = []
for item in stocks:
    ticker = item[0]
    name = item[1] if len(item) > 1 else item[0]
    
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period='3mo')
        info = tk.info
        
        if len(h) < 30:
            continue
        
        price = float(h['Close'].iloc[-1])
        rsi = calc_rsi(h['Close'], 14).iloc[-1]
        ma20 = h['Close'].rolling(20).mean().iloc[-1]
        ma60 = h['Close'].rolling(60).mean().iloc[-1] if len(h) >= 60 else ma20
        bias20 = (price / ma20 - 1) * 100
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        ret_3m = (price / float(h['Close'].iloc[0]) - 1) * 100
        
        pe = info.get('trailingPE', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0
        rec = info.get('recommendationKey', 'none')
        
        above = 'Y' if price > ma20 else 'N'
        above2 = 'Y' if price > ma60 else 'N'
        
        if rsi < 40:
            zone = '低估'
        elif rsi < 55:
            zone = '合理'
        elif rsi < 70:
            zone = '偏高'
        else:
            zone = '過熱'
        
        results.append({
            'ticker': ticker, 'name': name,
            'price': price, 'rsi': rsi, 'bias20': bias20,
            'above_ma20': above, 'above_ma60': above2, 'zone': zone,
            'ret_1m': ret_1m, 'ret_3m': ret_3m,
            'pe': pe, 'rev_growth': rev_growth, 'rec': rec
        })
    except:
        pass

results.sort(key=lambda x: x['rsi'])

print(f'共 {len(results)} 檔股票')
print()
print(f'{"代號":<6} {"名稱":<12} {"價格":>8} {"RSI":>5} {"區間":<6} {"MA20":>5} {"MA60":>5} {"1M":>7} {"3M":>7} {"PE":>6} {"評級":<10}')
print('-' * 90)
for r in results:
    pe_str = f'{r["pe"]:.0f}' if r['pe'] > 0 else 'N/A'
    rev = f'{r["rev_growth"]*100:.0f}%' if r['rev_growth'] else 'N/A'
    print(f'{r["ticker"]:<6} {r["name"]:<12} {r["price"]:>8.2f} {r["rsi"]:>5.1f} {r["zone"]:<6} {r["above_ma20"]:>5} {r["above_ma60"]:>5} {r["ret_1m"]:>7.1f} {r["ret_3m"]:>7.1f} {pe_str:>6} {r["rec"]:<10}')

print()
print('=' * 70)
print('分區總結')
print('=' * 70)

low_rsi = [r for r in results if r['rsi'] < 45]
mid_rsi = [r for r in results if 45 <= r['rsi'] < 60]
high_rsi = [r for r in results if r['rsi'] >= 60]

print(f'低估進場區 (RSI < 45): {len(low_rsi)} 檔')
for r in low_rsi:
    print(f'  - {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')

print(f'合理區 (RSI 45-60): {len(mid_rsi)} 檔')
for r in mid_rsi:
    print(f'  - {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')

print(f'偏高/過熱 (RSI >= 60): {len(high_rsi)} 檔')
for r in high_rsi:
    print(f'  - {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')