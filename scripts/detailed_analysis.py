import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def full_analysis(ticker, name, market='US', stype=''):
    try:
        if market == 'TW':
            tk = yf.Ticker(ticker + '.TW')
        else:
            tk = yf.Ticker(ticker)
        h = tk.history(period='3mo')
        info = tk.info
        
        if len(h) < 30:
            return None
        
        price = float(h['Close'].iloc[-1])
        rsi14 = calc_rsi(h['Close'], 14).iloc[-1]
        rsi5 = calc_rsi(h['Close'], 5).iloc[-1]
        ma5 = h['Close'].rolling(5).mean().iloc[-1]
        ma20 = h['Close'].rolling(20).mean().iloc[-1]
        ma60 = h['Close'].rolling(60).mean().iloc[-1] if len(h) >= 60 else ma20
        bias5 = (price / ma5 - 1) * 100
        bias20 = (price / ma20 - 1) * 100
        vol = h['Volume'].iloc[-1]
        vol20 = h['Volume'].rolling(20).mean().iloc[-1]
        
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        ret_3m = (price / float(h['Close'].iloc[0]) - 1) * 100
        
        pe = info.get('trailingPE', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0
        div = info.get('dividendYield', 0) or 0
        mktcap = info.get('marketCap', 0) / 1e9
        rec = info.get('recommendationKey', 'none')
        beta = info.get('beta', 0) or 0
        
        return {
            'ticker': ticker, 'name': name, 'market': market,
            'price': price, 'rsi14': rsi14, 'rsi5': rsi5,
            'ma5': ma5, 'ma20': ma20, 'ma60': ma60,
            'bias5': bias5, 'bias20': bias20,
            'vol_ratio': vol/vol20 if vol20 > 0 else 0,
            'ret_1m': ret_1m, 'ret_3m': ret_3m,
            'pe': pe, 'roe': roe, 'rev_growth': rev_growth,
            'div': div, 'mktcap': mktcap, 'rec': rec, 'beta': beta
        }
    except:
        return None

stocks = [
    ('2382', '廣達', 'TW', '短線波段'),
    ('4961', '力旺', 'TW', '短線波段'),
    ('00713', '元大高息低波', 'TW', 'DCA長抱'),
    ('DLO', 'Deloitte', 'US', '價值投資'),
    ('GEN', 'Gen', 'US', '價值投資'),
    ('RIVN', 'Rivian', 'US', '成長股'),
    ('DXCM', 'DexCom', 'US', '成長股'),
    ('BND', 'BND美債', 'US', 'DCA長抱'),
    ('VEA', 'VEA成熟市場', 'US', 'DCA長抱'),
]

for ticker, name, market, stype in stocks:
    r = full_analysis(ticker, name, market, stype)
    if r:
        print('=' * 60)
        print(f'{ticker} {name} [{stype}]')
        print('=' * 60)
        print(f'Price: {r["price"]:.2f} | RSI(14): {r["rsi14"]:.1f} | RSI(5): {r["rsi5"]:.1f}')
        print(f'MA5: {r["ma5"]:.2f} | MA20: {r["ma20"]:.2f} | MA60: {r["ma60"]:.2f}')
        print(f'Bias5: {r["bias5"]:+.2f}% | Bias20: {r["bias20"]:+.2f}%')
        print(f'1M: {r["ret_1m"]:+.2f}% | 3M: {r["ret_3m"]:+.2f}%')
        print(f'Vol ratio: {r["vol_ratio"]:.2f}x')
        print(f'PE: {r["pe"]:.1f} | ROE: {r["roe"]*100:.1f}%' if r["roe"] else 'PE: N/A')
        print(f'Rev growth: {r["rev_growth"]*100:.1f}%' if r["rev_growth"] else 'Rev growth: N/A')
        print(f'Div: {r["div"]*100:.2f}%' if r["div"] else 'Div: N/A')
        print(f'MktCap: {r["mktcap"]:.1f}B | Beta: {r["beta"]:.2f}')
        print(f'Rec: {r["rec"]}')
        
        # Entry zone
        if market == 'TW':
            entry_min, entry_max = (35, 45) if stype == '短線波段' else (40, 55)
        else:
            entry_min, entry_max = (35, 50) if stype in ['價值投資', '成長股'] else (40, 55)
        
        in_zone = entry_min <= r['rsi14'] <= entry_max
        above_ma20 = r['price'] > r['ma20']
        above_ma60 = r['price'] > r['ma60']
        
        print(f'Entry RSI range: {entry_min}-{entry_max} | Actual: {r["rsi14"]:.1f}')
        print(f'MA20 above: {"YES" if above_ma20 else "NO"} | MA60 above: {"YES" if above_ma60 else "NO"}')
        
        if in_zone and above_ma20:
            print('>>> RECOMMEND TO ENTER')
        elif in_zone:
            print('>>> WATCH - wait for MA20 breakout')
        else:
            print('>>> WAIT FOR PULLBACK')
        print()