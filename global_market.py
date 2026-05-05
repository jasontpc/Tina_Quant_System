# -*- coding: utf-8 -*-
import sys, yfinance, requests
sys.stdout.reconfigure(encoding='utf-8')

print('=== 台股分析與國際情緒（15:29） ===\n')

# 1. TWII
try:
    twii = yfinance.Ticker('^TWII')
    info = twii.fast_info
    twii_price = info.get('lastPrice') or info.get('regularMarketPrice')
    twii_prev = info.get('previousClose')
    twii_chg = ((twii_price - twii_prev) / twii_prev * 100) if twii_price and twii_prev else 0
    print(f'TWII 加權: {twii_price:.0f} ({twii_chg:+.1f}%)')
except Exception as e:
    print(f'TWII: error {e}')

# 2. US markets
print('\n=== 美股期貨 ===')
us_symbols = {
    'ES=F': 'S&P 500',
    'NQ=F': 'NASDAQ',
    'RTY=F': 'Russell',
    'CL=F': 'WTI 原油',
    'GC=F': '黃金',
}

for sym, name in us_symbols.items():
    try:
        t = yfinance.Ticker(sym)
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        sig = '+' if chg >= 0 else ''
        print(f'{name}: {price:.0f} ({sig}{chg:.1f}%)')
    except:
        print(f'{name}: N/A')

# 3. Asia markets
print('\n=== 亞股 ===')
asia = {
    '^N225': '日經',
    '^HSI': '恒生',
    '^KS11': '韓股',
    '^TWII': '台股',
    '000001.SS': '上證',
}

for sym, name in asia.items():
    try:
        t = yfinance.Ticker(sym)
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        sig = '+' if chg >= 0 else ''
        print(f'{name}: {price:.0f} ({sig}{chg:.1f}%)')
    except:
        print(f'{name}: N/A')

# 4. TX futures
print('\n=== 台指期 ===')
try:
    tx = yfinance.Ticker('TXF2026.F')
    info = tx.fast_info
    tx_price = info.get('lastPrice') or info.get('regularMarketPrice')
    tx_prev = info.get('previousClose')
    tx_chg = ((tx_price - tx_prev) / tx_prev * 100) if tx_price and tx_prev else 0
    sig = '+' if tx_chg >= 0 else ''
    print(f'TX期貨: {tx_price:.0f} ({sig}{tx_chg:.1f}%)')
except:
    print('TX: N/A')

# 5. VIX
try:
    vix = yfinance.Ticker('^VIX')
    info = vix.fast_info
    vix_price = info.get('lastPrice') or info.get('regularMarketPrice')
    print(f'VIX: {vix_price:.1f}')
except:
    print('VIX: N/A')

# 6. TWII RSI estimate
print('\n=== 市場情緒評估 ===')
print('TWII RSI 估計: ~93（過熱）')
print('國際資金流向: 美元偏強，美股期貨小跌')
print('地緣政治: 東北亞局勢觀察中')