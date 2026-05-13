# -*- coding: utf-8 -*-
import sys, yfinance, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

# Ray DCA watch list
etfs = {
    '0050.TW': '元大台灣50',
    '00646.TW': '富邦S&P500',
    '00662.TW': '富邦NASDAQ100',
    '00757.TW': '統一大FANG+',
    '00713.TW': '元大高息低波',
    '0056.TW': '元大高股息',
    '00927.TW': '統一手創未來',
}

print('=== Ray ETF 即時報價 ===')
print(f'{"代碼":<8} {"名稱":<12} {"價格":>10} {"漲跌%":>8}')
print('-' * 45)

for sym, name in etfs.items():
    try:
        ticker = yfinance.Ticker(sym)
        info = ticker.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        sig = '+' if chg >= 0 else ''
        print(f'{sym.replace(".TW",""):<8} {name:<12} {price:>10.2f} {sig}{chg:>7.1f}%')
    except Exception as e:
        print(f'{sym.replace(".TW",""):<8} {name:<12} error: {e}')

print()

# Check DCA prices
print('=== Ray 理想進場價 vs 目前 ===')
dca_prices = {
    '0050': {'ideal': 77, 'current': None},
    '00646': {'ideal': 66, 'current': None},
    '00662': {'ideal': 100, 'current': None},
    '00757': {'ideal': 110, 'current': None},
    '00713': {'ideal': 51, 'current': None},
    '0056': {'ideal': 38, 'current': None},
    '00927': {'ideal': 25, 'current': None},
}

# Get current prices
for sym in etfs.keys():
    try:
        ticker = yfinance.Ticker(sym)
        info = ticker.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        ticker_sym = sym.replace('.TW', '')
        if ticker_sym in dca_prices:
            dca_prices[ticker_sym]['current'] = price
    except:
        pass

print(f'{"代碼":<8} {"理想價":>8} {"目前價":>8} {"偏離":>8} {"狀態":<10}')
print('-' * 50)
for code, info in dca_prices.items():
    curr = info['current']
    ideal = info['ideal']
    if curr:
        diff = ((curr - ideal) / ideal) * 100
        sig = '+' if diff >= 0 else ''
        if diff < -5:
            status = '折扣好'
        elif diff < 0:
            status = '小幅折扣'
        elif diff < 10:
            status = '合理'
        else:
            status = '偏貴'
        print(f'{code:<8} {ideal:>8.0f} {curr:>8.2f} {sig}{diff:>7.1f}% {status:<10}')
    else:
        print(f'{code:<8} {ideal:>8.0f} {"N/A":>8} {"N/A":>8} {"N/A":<10}')