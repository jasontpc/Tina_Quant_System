import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

stocks = [
    ('VEA', 'Vanguard 成熟市場', 'ETF'),
    ('BND', 'BND 美債', 'ETF'),
    ('DLO', 'Deloitte', '價值'),
    ('GEN', 'Gen', '價值'),
    ('RIVN', 'Rivian', '成長'),
    ('RKLB', 'RocketLab', '成長'),
    ('DXCM', 'DexCom', '醫療'),
    ('NVDA', 'Nvidia', 'AI'),
    ('AMD', 'AMD', 'AI'),
    ('INTC', 'Intel', 'AI'),
    ('TSM', '台積電 ADR', '代工'),
]

print('US STOCK ANALYSIS')
print('='*65)

results = []
for item in stocks:
    ticker = item[0]
    name = item[1]
    stype = item[2]
    
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period='3mo')
        info = tk.info
        
        if len(h) < 30:
            continue
        
        price = float(h['Close'].iloc[-1])
        rsi = calc_rsi(h['Close'], 14).iloc[-1]
        ma20 = h['Close'].rolling(20).mean().iloc[-1]
        ma60 = h['Close'].rolling(60).mean().iloc[-1]
        bias20 = (price / ma20 - 1) * 100
        
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        
        pe = info.get('trailingPE', 0) or 0
        rev_g = info.get('revenueGrowth', 0) or 0
        rec = info.get('recommendationKey', 'none')
        
        above_ma20 = price > ma20
        above_ma60 = price > ma60
        
        if rsi < 40:
            zone = '低估'
        elif rsi < 55:
            zone = '合理'
        elif rsi < 70:
            zone = '偏高'
        else:
            zone = '過熱'
        
        results.append({
            'ticker': ticker, 'name': name, 'type': stype,
            'price': price, 'rsi': rsi, 'bias20': bias20,
            'above_ma20': above_ma20, 'above_ma60': above_ma60,
            'zone': zone, 'ret_1m': ret_1m, 'pe': pe, 'rev_g': rev_g, 'rec': rec
        })
    except:
        pass

results.sort(key=lambda x: x['rsi'])

print('Ticker  Name           Price    RSI  Zone    MA Status    1M      PE   Rec')
print('-'*75)
for r in results:
    pe_s = f'{r["pe"]:.0f}' if r['pe'] > 0 else 'N/A'
    rev_s = f'{r["rev_g"]*100:.0f}%' if r['rev_g'] else 'N/A'
    ma_str = 'MA20+' if r['above_ma20'] else 'MA20-'
    ma_str += ' MA60+' if r['above_ma60'] else ' MA60-'
    print(f"{r['ticker']:<6} {r['name']:<12} {r['price']:>8.2f} {r['rsi']:>5.1f} {r['zone']:<6} {ma_str:<12} {r['ret_1m']:>6.1f} {pe_s:>5} {r['rec']}")

print()
print('='*65)
print('RECOMMENDATIONS')
print('='*65)

entry_ok = [r for r in results if 35 <= r['rsi'] <= 65 and r['above_ma20']]
print(f'\n【Now Entry OK】({len(entry_ok)} stocks)')
for r in entry_ok:
    print(f'  - {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')

watch = [r for r in results if 35 <= r['rsi'] <= 65 and not r['above_ma20']]
print(f'\n【Wait for MA20 Breakout】({len(watch)} stocks)')
for r in watch:
    print(f'  - {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')

hot = [r for r in results if r['rsi'] >= 70]
print(f'\n【AVOID - Overheated】({len(hot)} stocks)')
for r in hot:
    print(f'  - {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')