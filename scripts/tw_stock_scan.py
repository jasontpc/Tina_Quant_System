import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

stocks = [
    ('2330','台積電','半導體'),
    ('2382','廣達','AI伺服器'),
    ('2454','聯發科','IC設計'),
    ('2317','鴻海','AI伺服器'),
    ('3034','緯穎','AI伺服器'),
    ('3665','穎崴','半導體'),
    ('4961','力旺','IC設計'),
    ('2881','富邦金','金融'),
    ('2884','玉山金','金融'),
    ('2891','中信金','金融'),
    ('2883','開發金','金融'),
    ('2886','兆豐金','金融'),
    ('2855','統一證','券商'),
    ('3231','緯創','AI伺服器'),
    ('3017','奇鋐','散熱'),
    ('2345','義隆','IC設計'),
    ('3717','耕興','網通'),
    ('2458','義隆電','IC設計'),
    ('2303','聯電','半導體'),
]

results = []
for item in stocks:
    ticker = item[0]
    name = item[1]
    stype = item[2]
    try:
        tk = yf.Ticker(ticker + '.TW')
        h = tk.history(period='3mo')
        info = tk.info
        if len(h) < 30:
            continue
        price = float(h['Close'].iloc[-1])
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        ma60 = float(h['Close'].rolling(60).mean().iloc[-1])
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

print('TW STOCK ANALYSIS')
print('='*70)
for r in results:
    pe_s = f'{r["pe"]:.1f}' if r['pe'] > 0 else 'N/A'
    rev_s = f'{r["rev_g"]*100:.0f}%' if r['rev_g'] else 'N/A'
    ma20_s = 'ABOVE' if r['above_ma20'] else 'BELOW'
    ma60_s = 'ABOVE' if r['above_ma60'] else 'BELOW'
    print(f"{r['ticker']} {r['name']} {r['price']} RSI={r['rsi']:.1f} {r['zone']} MA20={ma20_s} MA60={ma60_s} 1M={r['ret_1m']:.1f}% PE={pe_s} Rev={rev_s}")

entry = [r for r in results if 35 <= r['rsi'] <= 65 and r['above_ma20']]
wait = [r for r in results if 35 <= r['rsi'] <= 65 and not r['above_ma20']]
hot = [r for r in results if r['rsi'] >= 70]

print()
print('RECOMMENDATIONS')
print(f'Now Entry OK ({len(entry)} stocks):')
for r in entry:
    print(f'  {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')
print(f'Wait for MA20 ({len(wait)} stocks):')
for r in wait:
    print(f'  {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')
print(f'AVOID ({len(hot)} stocks):')
for r in hot:
    print(f'  {r["ticker"]} {r["name"]}: RSI {r["rsi"]:.1f}')