import sqlite3, json
from pathlib import Path
from datetime import datetime

DB = Path('data/yfinance.db')
WATCHLIST = 'data/team_watch_list.json'

with open(WATCHLIST, 'r', encoding='utf-8') as f:
    watch_data = json.load(f)['complete_watch']

# Flatten all watch list stocks
all_stocks = []
for team, stocks in watch_data.items():
    for s in stocks:
        all_stocks.append(s)

conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60
    FROM daily_ohlcv WHERE symbol IN (%s) ORDER BY symbol, date DESC
""" % ','.join("'%s'" % s for s in all_stocks[:50]))
rows = c.fetchall()
conn.close()

symbols = {}
for r in rows:
    sym = r[0]
    if sym not in symbols:
        symbols[sym] = r

results = []
for team, stocks in watch_data.items():
    for sym in stocks:
        if sym not in symbols:
            continue
        r = symbols[sym]
        price = r[2]
        rsi = r[3] or 50
        macd = r[4] or 0
        sma20 = r[5] or price
        sma60 = r[6] or price

        if not price or price <= 0:
            continue

        # DCA scoring - lower RSI is better for long-term entry
        score = 0
        tags = []

        if rsi < 30:
            score += 50; tags.append('EXCELLENT_ENTRY')
        elif rsi < 40:
            score += 40; tags.append('GOOD_ENTRY')
        elif rsi < 50:
            score += 25; tags.append('FAIR_ENTRY')
        elif rsi < 60:
            score += 10; tags.append('NEUTRAL')
        else:
            score += 0; tags.append('EXPENSIVE')

        if macd > 0:
            score += 10; tags.append('MACD_BULL')

        if sma20 > sma60:
            score += 5; tags.append('MA_BULL')

        results.append({
            'symbol': sym,
            'team': team,
            'price': price,
            'rsi': round(rsi, 1),
            'macd': round(macd, 4),
            'score': score,
            'tags': tags,
            'ma_bull': sma20 > sma60
        })

# Sort by RSI (lower = better for DCA) then by score
results.sort(key=lambda x: (x['rsi'], -x['score']))

print('='*65)
print('  Tina DCA Recommendations (TW + US)')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*65)
print()
print('DCA Strategy: Buy low RSI = better long-term entry')
print('Lower RSI = better entry price for Dollar Cost Averaging')
print()

# TW and US separation
tw_results = [r for r in results if '.TW' in r['symbol'] or '.TWO' in r['symbol']]
us_results = [r for r in results if '.TW' not in r['symbol'] and '.TWO' not in r['symbol']]

print('[Taiwan Stocks - DCA Candidates]')
print('%-12s %-8s %6s %8s %5s %s' % ('Symbol', 'Team', 'Price', 'RSI', 'Score', 'Tags'))
print('-'*65)
for r in tw_results[:10]:
    rsi_flag = 'GREEN' if r['rsi'] < 40 else ('YELLOW' if r['rsi'] < 55 else 'RED')
    print('%s %-8s %8.2f %s(%.1f) %d %s' % (
        r['symbol'], r['team'], r['price'], rsi_flag[:1], r['rsi'],
        r['score'], ', '.join(r['tags'][:2])))

print()
print('[US Stocks - DCA Candidates]')
if us_results:
    print('%-10s %-8s %9s %6s %5s %s' % ('Symbol', 'Team', 'Price', 'RSI', 'Score', 'Tags'))
    print('-'*65)
    for r in us_results[:10]:
        rsi_flag = 'GREEN' if r['rsi'] < 40 else ('YELLOW' if r['rsi'] < 55 else 'RED')
        print('%s %-8s %10.2f %s(%.1f) %d %s' % (
            r['symbol'], r['team'], r['price'], rsi_flag[:1], r['rsi'],
            r['score'], ', '.join(r['tags'][:2])))
else:
    print('  No US stocks in watch list')

print()
print('='*65)
print('[DCA Entry Guide]')
print()
print('GREEN  (RSI < 40): Excellent entry - Start/Add DCA')
print('YELLOW (RSI 40-55): Acceptable entry - Continue DCA')
print('RED    (RSI > 55): Wait for better entry - Pause DCA')
print()
print('[Recommended DCA Schedule]')
tw_top = tw_results[:3] if tw_results else []
us_top = us_results[:2] if us_results else []

if tw_top:
    print('TW: %s' % ', '.join(r['symbol'] for r in tw_top))
if us_top:
    print('US: %s' % ', '.join(r['symbol'] for r in us_top))