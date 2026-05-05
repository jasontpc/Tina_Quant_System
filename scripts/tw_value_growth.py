import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

stocks = [
    ('2330', '台積電'),
    ('2382', '廣達'),
    ('2454', '聯發科'),
    ('2317', '鴻海'),
    ('3034', '緯穎'),
    ('3665', '穎崴'),
    ('4961', '力旺'),
    ('2881', '富邦金'),
    ('2884', '玉山金'),
    ('2891', '中信金'),
    ('2883', '開發金'),
    ('2886', '兆豐金'),
    ('2855', '統一證'),
    ('2345', '義隆'),
    ('3017', '奇鋐'),
    ('3231', '健鼎'),
    ('3717', '耕興'),
    ('2458', '義隆電'),
]

print('TW Value/Growth 分類分析')
print('=' * 70)

value = []
growth = []
for item in stocks:
    ticker = item[0]
    name = item[1]
    try:
        tk = yf.Ticker(ticker + '.TW')
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
        roe = info.get('returnOnEquity', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0
        pb = info.get('priceToBook', 0) or 0
        mktcap = info.get('marketCap', 0) / 1e9
        div = info.get('dividendYield', 0) or 0
        rec = info.get('recommendationKey', 'none')
        
        above_ma20 = price > ma20
        above_ma60 = price > ma60
        
        rec_dict = {'strong_buy': 5, 'buy': 4, 'outperform': 4, 'hold': 3, 'neutral': 3, 'underperform': 2, 'sell': 1, 'none': 2}
        rec_score = rec_dict.get(rec, 2)
        
        # Value vs Growth classification
        is_value = pe > 0 and pe < 20 and roe and roe > 8
        is_growth = rev_growth and rev_growth > 0.2
        
        entry_ok = 35 <= rsi <= 65
        ma_ok = above_ma20
        
        signal_score = 0
        if entry_ok: signal_score += 2
        if ma_ok: signal_score += 1
        if pe > 0 and pe < 25: signal_score += 1
        if roe and roe > 10: signal_score += 1
        if is_growth: signal_score += 2
        signal_score += rec_score // 2
        
        d = {
            'ticker': ticker, 'name': name, 'price': price,
            'rsi': rsi, 'bias20': bias20,
            'pe': pe, 'roe': roe*100 if roe else 0, 'rev_growth': rev_growth*100 if rev_growth else 0,
            'pb': pb, 'mktcap': mktcap, 'div': div*100 if div else 0,
            'above_ma20': above_ma20, 'above_ma60': above_ma60,
            'ret_1m': ret_1m, 'ret_3m': ret_3m,
            'rec': rec, 'signal_score': signal_score,
            'is_value': is_value, 'is_growth': is_growth,
            'entry_ok': entry_ok, 'ma_ok': ma_ok
        }
        
        if is_value:
            value.append(d)
        if is_growth:
            growth.append(d)
    except:
        pass

# Sort by signal score
value.sort(key=lambda x: -x['signal_score'])
growth.sort(key=lambda x: -x['signal_score'])

print()
print('=' * 70)
print('VALUE STARS（價值股：PE<20 + ROE>8%）')
print('=' * 70)
print(f'{"代號":<6} {"名稱":<8} {"價格":>8} {"RSI":>5} {"PE":>5} {"ROE":>6} {"PB":>5} {"DIV":>5} {"1M":>6} {"信號":>5}')
print('-' * 70)
for d in value[:10]:
    pe_str = f'{d["pe"]:.1f}' if d['pe'] > 0 else 'N/A'
    roe_str = f'{d["roe"]:.1f}' if d['roe'] else 'N/A'
    pb_str = f'{d["pb"]:.1f}' if d['pb'] else 'N/A'
    div_str = f'{d["div"]:.1f}%' if d['div'] else 'N/A'
    ma = 'MA20+' if d['above_ma20'] else 'MA20-'
    entry = 'OK' if d['entry_ok'] else 'NG'
    print(f'{d["ticker"]:<6} {d["name"]:<8} {d["price"]:>8.2f} {d["rsi"]:>5.1f} {pe_str:>5} {roe_str:>6} {pb_str:>5} {div_str:>5} {d["ret_1m"]:>6.1f} {d["signal_score"]:>5}')

print()
print('=' * 70)
print('GROWTH STARS（成長股：營收成長>20%）')
print('=' * 70)
print(f'{"代號":<6} {"名稱":<8} {"價格":>8} {"RSI":>5} {"營收":>6} {"PE":>5} {"ROE":>6} {"1M":>6} {"3M":>7} {"信號":>5}')
print('-' * 70)
for d in growth[:10]:
    pe_str = f'{d["pe"]:.1f}' if d['pe'] > 0 else 'N/A'
    roe_str = f'{d["roe"]:.1f}' if d['roe'] else 'N/A'
    ma = 'MA20+' if d['above_ma20'] else 'MA20-'
    entry = 'OK' if d['entry_ok'] else 'NG'
    print(f'{d["ticker"]:<6} {d["name"]:<8} {d["price"]:>8.2f} {d["rsi"]:>5.1f} {d["rev_growth"]:>6.1f} {pe_str:>5} {roe_str:>6} {d["ret_1m"]:>6.1f} {d["ret_3m"]:>7.1f} {d["signal_score"]:>5}')

print()
print('=' * 70)
print('RECOMMENDATIONS（可進場）')
print('=' * 70)
print()
print('【價值股首選】')
for d in value:
    if d['entry_ok'] and d['ma_ok']:
        print(f'  {d["ticker"]} {d["name"]}: RSI {d["rsi"]:.1f}, PE {d["pe"]:.1f}, ROE {d["roe"]:.1f}%')

print()
print('【成長股首選】')
for d in growth:
    if d['entry_ok'] and d['ma_ok']:
        print(f'  {d["ticker"]} {d["name"]}: RSI {d["rsi"]:.1f}, 營收 {d["rev_growth"]:.1f}%, MA20+')

print()
print('【等待回調】')
for d in value + growth:
    if d['entry_ok'] and not d['ma_ok']:
        print(f'  {d["ticker"]} {d["name"]}: RSI {d["rsi"]:.1f} OK, 等MA20突破')