import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_stock_data(ticker, is_tw=False):
    try:
        t = yf.Ticker(ticker + '.TW' if is_tw else ticker)
        h = t.history(period='3mo')
        if len(h) < 30:
            return None
        price = float(h['Close'].iloc[-1])
        info = t.info
        rsi = calc_rsi(h['Close'], 14).iloc[-1]
        ma20 = h['Close'].rolling(20).mean().iloc[-1]
        ma60 = h['Close'].rolling(60).mean().iloc[-1] if len(h) >= 60 else ma20
        bias = (price / ma20 - 1) * 100
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        return {
            'price': price,
            'rsi': rsi,
            'ma20': ma20,
            'ma60': ma60,
            'bias': bias,
            'ret_1m': ret_1m,
            'pe': info.get('trailingPE', 0) or 0,
            'mktcap': info.get('marketCap', 0) / 1e9,
            'div': info.get('dividendYield', 0) or 0
        }
    except:
        return None

# === NANA: Taiwan Band Wave Stocks ===
nana_stocks = [
    ('2330', '台積電'), ('2382', '廣達'), ('3665', '穎崴'),
    ('2317', '鴻海'), ('3034', '緯穎')
]

# === LEO: Taiwan AI Tech ===
leo_stocks = [
    ('2454', '聯發科'), ('2345', '智邦'), ('3017', '奇鋐'),
    ('3034', '緯穎'), ('4961', '力旺')
]

# === RAY: Taiwan ETFs ===
ray_etfs = [
    ('0050', '元大台灣50'), ('00646', '富邦S&P500'),
    ('00713', '元大高息低波'), ('0056', '元大高股息')
]

# === MAGGY: US Stocks ===
maggy_stocks = [
    ('D', 'Dominion'), ('BMY', 'Bristol-Myers'), ('SO', 'Southern'),
    ('DXCM', 'DexCom'), ('COIN', 'Coinbase'), ('NET', 'Cloudflare')
]

# === US Growth Under $100 ===
us_growth = [
    ('RIVN', 'Rivian'), ('SMCI', 'Super Micro'), ('SOFI', 'SoFi'),
    ('PATH', 'UiPath'), ('GTLB', 'GitLab'), ('U', 'Unity'),
    ('BILL', 'Bill'), ('ESTC', 'Elastic'), ('FUBO', 'FuboTV')
]

# === Leverage ETFs ===
leverage = [
    ('SOXL', '半導體3x'), ('TQQQ', 'Nasdaq3x'), ('SPXL', 'S&P500 3x'),
    ('SQQQ', 'Nasdaq-3x'), ('SDS', 'S&P500-2x'), ('TNA', 'SmallCap 3x')
]

print("=" * 80)
print("TINA QUANT SYSTEM — ALL TEAMS WATCHLIST REPORT")
print("=" * 80)

# NANA
print("\n【NANA — 台股波段觀察名單】")
print(f"{'代號':<6} {'名稱':<8} {'現價':>8} {'RSI':>6} {'BIAS20':>8} {'1M%':>7} {'MA排列':<10}")
print("-" * 60)
for ticker, name in nana_stocks:
    d = get_stock_data(ticker, True)
    if d:
        above_ma20 = d['price'] > d['ma20']
        above_ma60 = d['price'] > d['ma60']
        ma_status = "多頭" if (above_ma20 and above_ma60) else "震盪"
        print(f"{ticker:<6} {name:<8} {d['price']:>8.2f} {d['rsi']:>6.1f} {d['bias']:>+7.1f}% {d['ret_1m']:>+6.1f}% {ma_status}")

# LEO
print("\n【LEO — 台股AI科技觀察名單】")
print(f"{'代號':<6} {'名稱':<8} {'現價':>8} {'RSI':>6} {'BIAS20':>8} {'1M%':>7} {'MA排列':<10}")
print("-" * 60)
for ticker, name in leo_stocks:
    d = get_stock_data(ticker, True)
    if d:
        above_ma20 = d['price'] > d['ma20']
        above_ma60 = d['price'] > d['ma60']
        ma_status = "多頭" if (above_ma20 and above_ma60) else "震盪"
        print(f"{ticker:<6} {name:<8} {d['price']:>8.2f} {d['rsi']:>6.1f} {d['bias']:>+7.1f}% {d['ret_1m']:>+6.1f}% {ma_status}")

# RAY
print("\n【RAY — 台股ETF觀察名單】")
print(f"{'代號':<6} {'名稱':<12} {'現價':>8} {'RSI':>6} {'BIAS20':>8} {'1M%':>7} {'區間':<12}")
print("-" * 65)
for ticker, name in ray_etfs:
    d = get_stock_data(ticker, True)
    if d:
        print(f"{ticker:<6} {name:<12} {d['price']:>8.2f} {d['rsi']:>6.1f} {d['bias']:>+7.1f}% {d['ret_1m']:>+6.1f}% {'合理' if d['rsi']<65 else '偏貴'}")

# MAGGY
print("\n【MAGGY — 美股價值成長觀察名單】")
print(f"{'代號':<6} {'名稱':<12} {'現價':>8} {'RSI':>6} {'BIAS20':>8} {'1M%':>7} {'P/E':>7} {'Div':>6}")
print("-" * 65)
for ticker, name in maggy_stocks:
    d = get_stock_data(ticker, False)
    if d:
        print(f"{ticker:<6} {name:<12} ${d['price']:>7.2f} {d['rsi']:>6.1f} {d['bias']:>+7.1f}% {d['ret_1m']:>+6.1f}% {d['pe']:>7.1f} {d['div']*100:>5.2f}%")

# US Growth
print("\n【美股百元成長股觀察名單】")
print(f"{'代號':<6} {'名稱':<10} {'現價':>8} {'RSI':>6} {'BIAS20':>8} {'1M%':>7} {'區間':<10}")
print("-" * 60)
for ticker, name in us_growth:
    d = get_stock_data(ticker, False)
    if d:
        zone = "低估" if d['rsi'] < 45 else "合理" if d['rsi'] < 60 else "偏貴"
        print(f"{ticker:<6} {name:<10} ${d['price']:>7.2f} {d['rsi']:>6.1f} {d['bias']:>+7.1f}% {d['ret_1m']:>+6.1f}% {zone}")

# Leverage
print("\n【槓桿ETF觀察名單】")
print(f"{'代號':<6} {'名稱':<10} {'現價':>8} {'RSI':>6} {'BIAS20':>8} {'1M%':>7} {'操作':<10}")
print("-" * 65)
for ticker, name in leverage:
    d = get_stock_data(ticker, False)
    if d:
        if d['rsi'] > 70:
            op = "⚠️ 過熱"
        elif d['rsi'] < 30:
            op = "📗 低估"
        else:
            op = "📊 中性"
        print(f"{ticker:<6} {name:<10} ${d['price']:>7.2f} {d['rsi']:>6.1f} {d['bias']:>+7.1f}% {d['ret_1m']:>+6.1f}% {op}")

print("\n" + "=" * 80)
print("報告完成")
print("=" * 80)