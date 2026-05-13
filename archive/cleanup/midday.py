# -*- coding: utf-8 -*-
import sys, yfinance, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

print('=== 盤中分析（13:21） ===\n')

# TX futures via yfinance
try:
    tx = yfinance.Ticker('TXF2026.F')
    info = tx.fast_info
    price = info.get('lastPrice') or info.get('regularMarketPrice')
    prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
    chg = ((price - prev) / prev * 100) if price and prev else 0
    print(f'TX期貨: {price:.0f} ({chg:+.1f}%)')
except Exception as e:
    print(f'TX: error {e}')

# TWII
try:
    twii = yfinance.Ticker('^TWII')
    info = twii.fast_info
    price = info.get('lastPrice') or info.get('regularMarketPrice')
    prev = info.get('previousClose')
    chg = ((price - prev) / prev * 100) if price and prev else 0
    print(f'TWII加權: {price:.0f} ({chg:+.1f}%)')
except Exception as e:
    print(f'TWII: error {e}')

# Nana candidates
print('\n=== Nana 候選股 ===')
etfs = ['2330.TW', '2454.TW', '2303.TW', '2317.TW', '3034.TW', '2382.TW', '3665.TW']
names = {'2330.TW':'台積電','2454.TW':'聯發科','2303.TW':'聯電','2313.TW':'鴻海','3034.TW':'緯穎','2382.TW':'廣達','3665.TW':'穎崴'}
for sym in etfs:
    try:
        t = yfinance.Ticker(sym)
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        n = names.get(sym, sym.replace('.TW',''))
        sig = '+' if chg >= 0 else ''
        print(f'{n:<6} {price:>10.0f} {sig}{chg:>6.1f}%')
    except:
        pass

# ETF DCA prices
print('\n=== Ray ETF ===')
etfs2 = ['0050.TW', '00646.TW', '00713.TW', '0056.TW']
dca_ideal = {'0050':77,'00646':66,'00713':51,'0056':38}
for sym in etfs2:
    try:
        t = yfinance.Ticker(sym)
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        code = sym.replace('.TW','')
        ideal = dca_ideal.get(code, 0)
        diff = ((price - ideal) / ideal * 100) if ideal else 0
        sig = '+' if chg >= 0 else ''
        print(f'{code:<6} {price:>8.2f} {sig}{chg:>5.1f}% | 理想:{ideal} 偏離:{diff:+.0f}%')
    except:
        pass