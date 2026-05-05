import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path('data/yfinance.db')

conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60, volume
    FROM daily_ohlcv
    WHERE symbol NOT LIKE '%.TW' AND symbol NOT LIKE '%.TWO'
    ORDER BY symbol, date DESC
""")
rows = c.fetchall()
conn.close()

symbols = {}
for r in rows:
    sym = r[0]
    if sym not in symbols:
        symbols[sym] = r

BLACKLIST = {'YANG', 'SOXS', 'TNA', 'SOXL', 'NUGT', 'JDST', 'KOLD'}

results = []
for sym, r in symbols.items():
    if sym in BLACKLIST:
        continue

    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0
    sma20 = r[5] or price
    sma60 = r[6] or price

    if not price or price <= 0 or price > 10000:
        continue

    score = 0
    tags = []

    if 25 <= rsi <= 40:
        score += 35; tags.append('RSI_Entry_Zone')
    elif 40 < rsi <= 55:
        score += 20; tags.append('RSI_Low')
    elif 55 < rsi <= 65:
        score += 5; tags.append('RSI_Neutral')
    else:
        continue

    if macd > 0:
        score += 25; tags.append('MACD_Bull')
    elif macd > -0.3:
        score += 10; tags.append('MACD_Near_Zero')

    if sma20 > sma60:
        score += 15; tags.append('MA_Bull')

    if score >= 30:
        results.append({
            'symbol': sym,
            'price': price,
            'rsi': round(rsi, 1),
            'macd': round(macd, 4),
            'sma20': round(sma20, 2),
            'sma60': round(sma60, 2),
            'score': score,
            'tags': tags,
            'ma_bull': sma20 > sma60
        })

results.sort(key=lambda x: x['score'], reverse=True)

print('='*65)
print('  Tina US Stock Recommendations (Blacklist Applied)')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*65)
print()

buys = [r for r in results if r['score'] >= 60]
watches = [r for r in results if 40 <= r['score'] < 60]

print('[BUY Signal] (Score >= 60)')
if buys:
    print('%-10s %9s %5s %8s %5s %s' % ('Symbol', 'Price', 'RSI', 'MACD', 'Score', 'Tags'))
    print('-'*60)
    for r in buys:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        print('%s %10.2f %s(%.1f) %s(%.3f) %d %s' % (
            r['symbol'], r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], ', '.join(r['tags'])))
else:
    print('  None')

print()
print('[WATCH List] (Score 40-59)')
if watches:
    print('%-10s %9s %5s %8s %5s %s' % ('Symbol', 'Price', 'RSI', 'MACD', 'Score', 'Tags'))
    print('-'*60)
    for r in watches[:12]:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        ma_flag = 'Bull' if r['ma_bull'] else 'Bear'
        print('%s %10.2f %s(%.1f) %s(%.3f) %s %d %s' % (
            r['symbol'], r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], ma_flag, r['score'], ', '.join(r['tags'])))
    if len(watches) > 12:
        print('  ...+%d more' % (len(watches) - 12))
else:
    print('  None')

print()
print('='*65)
print('[Summary]')
if buys:
    print('BUY: %s' % ', '.join(r['symbol'] for r in buys))
if watches:
    print('WATCH: %s' % ', '.join(r['symbol'] for r in watches[:8]))
print()
print('Blacklist: %s' % ', '.join(BLACKLIST))