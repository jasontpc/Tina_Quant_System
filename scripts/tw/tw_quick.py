# -*- coding: utf-8 -*-
import yfinance as yf

data = [
    ('^TWII', '加權指數'),
    ('^TPEx', '櫃買指數'),
    ('2330.TW', 'TSMC 2330'),
    ('2454.TW', '聯發科 2454'),
    ('2317.TW', '鴻海 2317'),
    ('2303.TW', '聯電 2303'),
    ('2603.TW', '長榮 2603'),
    ('2881.TW', '富邦金'),
    ('2308.TW', '台達電'),
    ('2451.TW', '友達'),
]

print('=' * 65)
print('  台股即時報價 2026-05-13 09:17 GMT+8')
print('=' * 65)

for ticker, name in data:
    try:
        h = yf.Ticker(ticker).history(period='5d')
        if len(h) >= 2:
            p = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            chg = (p - prev) / prev * 100
            print(f'{name:<14} {p:>9.2f}  {chg:>+6.2f}%')
        else:
            print(f'{name:<14} --')
    except Exception as e:
        print(f'{name:<14} Error')

# VIX
try:
    v = yf.Ticker('^VIX').history(period='1d')
    print(f'\nVIX: {v["Close"].iloc[-1]:.2f}')
except:
    print('\nVIX: --')