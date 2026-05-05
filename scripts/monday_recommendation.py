import sqlite3
from pathlib import Path
from datetime import datetime

DATA = Path('data')
DB = DATA / 'yfinance.db'

conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60 FROM daily_ohlcv WHERE symbol IN ('2330.TW','2382.TW','2634.TW','2313.TW','2881.TW','2892.TW','MSFT','CRM','00713.TW','2464.TW') ORDER BY date DESC")
rows = c.fetchall()
conn.close()

symbols = {}
for r in rows:
    sym = r[0]
    if sym not in symbols:
        symbols[sym] = r

print('='*60)
print('  Tina Monday Opening Recommendations')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*60)
print()

results = []
for sym, r in sorted(symbols.items()):
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0
    sma20 = r[5] or price
    sma60 = r[6] or price
    ma_bull = sma20 > sma60

    score = 0
    tags = []

    if 25 <= rsi <= 40:
        score += 30; tags.append('RSI_Entry')
    elif 40 < rsi <= 55:
        score += 20; tags.append('RSI_Low')
    elif 55 < rsi <= 65:
        score += 5

    if macd > 0:
        score += 20; tags.append('MACD_Bull')
    if ma_bull:
        score += 10; tags.append('MA_Bull')

    verdict = 'BUY' if score >= 60 else ('WATCH' if score >= 40 else 'HOLD')
    results.append((sym, price, rsi, macd, ma_bull, score, verdict, tags))

    rsi_flag = 'H' if rsi > 70 else ('G' if rsi < 40 else 'Y')
    macd_flag = 'Up' if macd > 0 else 'Dn'
    ma_flag = 'Up' if ma_bull else 'Dn'

    print('%s: $%.2f' % (sym, price))
    print('  RSI=%s(%.1f) | MACD=%s(%.3f) | MA=%s | Score=%d' % (rsi_flag, rsi, macd_flag, macd, ma_flag, score))
    print('  Verdict: %s | %s' % (verdict, ', '.join(tags)))
    print()

print('='*60)
print('SUMMARY')
buys = [r for r in results if r[6] == 'BUY']
watches = [r for r in results if r[6] == 'WATCH']
if buys:
    print('BUY: %s' % ', '.join(r[0] for r in sorted(buys, key=lambda x: -x[5])))
if watches:
    print('WATCH: %s' % ', '.join(r[0] for r in sorted(watches, key=lambda x: -x[5])))
if not buys and not watches:
    print('No clear signals - HOLD')