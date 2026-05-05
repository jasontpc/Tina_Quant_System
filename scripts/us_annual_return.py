import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_annualized(start_price, end_price, years):
    if start_price <= 0 or years <= 0:
        return 0
    return ((end_price / start_price) ** (1/years) - 1) * 100

print('='*70)
print('US STOCKS - 年化報酬率分析')
print('='*70)

stocks = [
    ('DLO', 'Deloitte', '5y'),
    ('GEN', 'Gen Digital', '5y'),
    ('RIVN', 'Rivian', '3y'),
    ('SOFI', 'SoFi', '3y'),
    ('RKLB', 'RocketLab', '2y'),
    ('DXCM', 'DexCom', '5y'),
    ('PATH', 'UiPath', '3y'),
    ('BILL', 'Bill Holdings', '3y'),
]

# Major ETFs
etfs = [
    ('SPY', 'S&P 500 ETF', '10y'),
    ('QQQ', 'Nasdaq 100 ETF', '10y'),
    ('VEA', 'Vanguard EM', '5y'),
    ('VYM', 'High Dividend', '5y'),
    ('SCHD', 'Schwab Div', '5y'),
]

results = []

print()
print('[ETFs - 長期投資]')
print('-'*70)
for ticker, name, period in etfs:
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period=period)
        if len(h) < 100:
            continue
        
        price = float(h['Close'].iloc[-1])
        start_price = float(h['Close'].iloc[0])
        
        years = float(period.replace('y',''))
        ann = calc_annualized(start_price, price, years)
        total = (price / start_price - 1) * 100
        
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        
        results.append({'ticker': ticker, 'name': name, 'ann': ann, 'total': total, 'rsi': rsi, 'type': 'ETF'})
        
        print(f'{ticker:<6} {name:<20} {ann:>6.1f}%/年 (總 {total:>7.1f}%) RSI={rsi:.1f}')
    except Exception as e:
        print(f'{ticker}: Error - {e}')

print()
print('[STOCKS - 成長股]')
print('-'*70)
for ticker, name, period in stocks:
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period=period)
        if len(h) < 50:
            continue
        
        price = float(h['Close'].iloc[-1])
        start_price = float(h['Close'].iloc[0])
        
        years = float(period.replace('y',''))
        ann = calc_annualized(start_price, price, years)
        total = (price / start_price - 1) * 100
        
        rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
        
        results.append({'ticker': ticker, 'name': name, 'ann': ann, 'total': total, 'rsi': rsi, 'type': 'STOCK'})
        
        print(f'{ticker:<6} {name:<20} {ann:>6.1f}%/年 (總 {total:>7.1f}%) RSI={rsi:.1f}')
    except Exception as e:
        print(f'{ticker}: Error - {e}')

# Sort by annualized return
results.sort(key=lambda x: x['ann'], reverse=True)

print()
print('='*70)
print('TOP PICKS - 按年化報酬排序')
print('='*70)
for r in results[:10]:
    rsi_flag = '*' if r['rsi'] > 70 else '+' if r['rsi'] < 40 else ' '
    print(f'{r["type"]:<5} {r["ticker"]:<6} {r["name"]:<20} {r["ann"]:>6.1f}%/年   RSI={r["rsi"]:.1f}{rsi_flag}')