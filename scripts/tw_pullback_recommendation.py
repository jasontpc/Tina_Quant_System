import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB = Path('data/yfinance.db')

conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60, volume
    FROM daily_ohlcv
    WHERE (symbol LIKE '%.TW' OR symbol LIKE '%.TWO')
    ORDER BY symbol, date DESC
""")
rows = c.fetchall()
conn.close()

symbols = {}
for r in rows:
    sym = r[0]
    if sym not in symbols:
        symbols[sym] = r

results = []
for sym, r in symbols.items():
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0
    sma20 = r[5] or price
    sma60 = r[6] or price

    if not price or price <= 0:
        continue

    if rsi < 40 or (40 <= rsi <= 55 and macd > 0 and sma20 > sma60):
        score = 0
        tags = []

        if rsi < 35:
            score += 40; tags.append('RSI_OVERSOLD')
        elif rsi < 45:
            score += 25; tags.append('RSI_LOW')
        elif rsi <= 55:
            score += 15; tags.append('RSI_NEUTRAL')

        if macd > 0.3:
            score += 25; tags.append('MACD_STRONG')
        elif macd > 0:
            score += 15; tags.append('MACD_POSITIVE')

        if sma20 > sma60:
            score += 15; tags.append('MA_BULL')

        if score >= 45:
            results.append({
                'symbol': sym,
                'price': price,
                'rsi': round(rsi, 1),
                'macd': round(macd, 4),
                'score': score,
                'tags': tags,
                'trend': 'UP' if sma20 > sma60 else 'NEUTRAL'
            })

results.sort(key=lambda x: x['score'], reverse=True)

print('='*65)
print('  Tina TW Pullback Candidates')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*65)
print()

strong = [r for r in results if r['score'] >= 60]
moderate = [r for r in results if 45 <= r['score'] < 60]

print('[Tier 1: Strong Pullback] (Score >= 60)')
if strong:
    for r in strong:
        print('  %s %.2f RSI=%.1f MACD=%.3f %s | %s' % (
            r['symbol'], r['price'], r['rsi'], r['macd'], r['trend'], ', '.join(r['tags'])))
else:
    print('  None')

print()
print('[Tier 2: Moderate Pullback] (Score 45-59)')
if moderate:
    for r in moderate[:10]:
        print('  %s %.2f RSI=%.1f MACD=%.3f %s | %s' % (
            r['symbol'], r['price'], r['rsi'], r['macd'], r['trend'], ', '.join(r['tags'])))
else:
    print('  None')

print()
print('='*65)
print('[Strategy]')
print()
print('  Pullback Entry Rules:')
print('  1. Only buy if MA still bullish (SMA20 > SMA60)')
print('  2. Enter when RSI hits 35-45 zone')
print('  3. MACD must stay positive (trend not broken)')
print('  4. Scale in gradually, no all-in')
print()
print('  Ideal timing:')
print('  - TWII pullback 3-5%, RSI drops to 40-50')
print('  - Target stock RSI in 30-45 range')
print('  - MACD still above zero')
print()
print('  WARNING: Do NOT buy RSI>60 pullbacks')
print()

if strong:
    print('[Top Picks]')
    for r in strong[:3]:
        sl = r['price'] * 0.94
        tp = r['price'] * 1.10
        print('  %s: Entry $%.2f | Stop $%.2f | Target $%.2f' % (r['symbol'], r['price'], sl, tp))