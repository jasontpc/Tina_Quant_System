import sqlite3
from pathlib import Path
from datetime import datetime
import json

DB = Path('data/yfinance.db')

conn = sqlite3.connect(str(DB))
c = conn.cursor()

# Get latest data for all TW stocks
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60, volume
    FROM daily_ohlcv
    WHERE symbol LIKE '%.TW' OR symbol LIKE '%.TWO'
    ORDER BY symbol, date DESC
""")
rows = c.fetchall()

# Get latest for each symbol
symbols = {}
for r in rows:
    sym = r[0]
    if sym not in symbols:
        symbols[sym] = r

# Load team watch list for priority
try:
    with open('data/team_watch_list.json', 'r', encoding='utf-8') as f:
        team_data = json.load(f)
    priority_stocks = set()
    for team_name, team_info in team_data.get('teams', {}).items():
        for s in team_info.get('watch_list', []):
            priority_stocks.add(s)
except:
    priority_stocks = set()

results = []
for sym, r in symbols.items():
    date = r[1]
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0
    sma20 = r[5] or price
    sma60 = r[6] or price
    vol = r[7] or 0

    if price is None or price <= 0:
        continue

    # Calculate score
    score = 0
    tags = []

    # RSI scoring (25-55 range, outside = 0)
    if 25 <= rsi <= 40:
        score += 35; tags.append('RSI超賣')
    elif 40 < rsi <= 55:
        score += 20; tags.append('RSI偏低')
    elif 55 < rsi <= 65:
        score += 5; tags.append('RSI中性')
    else:
        continue  # Skip overbought

    # MACD scoring
    if macd > 0:
        score += 25; tags.append('MACD多頭')
    elif macd > -0.5:
        score += 10; tags.append('MACD接近零軸')
    else:
        continue  # Skip strong bearish MACD

    # MA scoring
    if sma20 > sma60:
        score += 15; tags.append('MA多頭排列')

    # Volume check (need avg vol)
    c.execute("SELECT volume FROM daily_ohlcv WHERE symbol=? ORDER BY date DESC LIMIT 20", (sym,))
    vols = [r[0] for r in c.fetchall() if r[0]]
    if len(vols) >= 5:
        avg_vol = sum(vols) / len(vols)
        if vol > avg_vol * 1.3:
            score += 10; tags.append('量能放大')

    if score >= 45:
        results.append({
            'symbol': sym,
            'price': price,
            'rsi': round(rsi, 1),
            'macd': round(macd, 4),
            'ma_bull': sma20 > sma60,
            'score': score,
            'tags': tags,
            'priority': sym in priority_stocks
        })

conn.close()

print('='*60)
print('  Tina 台股週一買入建議')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*60)
print()

# Sort by score descending, priority first
results.sort(key=lambda x: (x['priority'], x['score']), reverse=True)

buys = [r for r in results if r['score'] >= 60]
watches = [r for r in results if r['score'] >= 45 and r['score'] < 60]

print('【BUY 訊號】(Score >= 60)')
if buys:
    print('%-12s %9s %5s %8s %5s %s' % ('代號', '價格', 'RSI', 'MACD', '分數', '標籤'))
    print('-'*55)
    for r in buys:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        pri = '*' if r['priority'] else ''
        print('%s%s %9.2f %s(%.1f) %s(%.3f) %d %s' % (
            r['symbol'], pri, r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], ', '.join(r['tags'])))
else:
    print('  無 BUY 訊號')

print('\n【WATCH 觀察】(Score 45-59)')
if watches:
    print('%-12s %9s %5s %8s %5s %s' % ('代號', '價格', 'RSI', 'MACD', '分數', '標籤'))
    print('-'*55)
    for r in watches[:10]:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        pri = '*' if r['priority'] else ''
        print('%s%s %9.2f %s(%.1f) %s(%.3f) %d %s' % (
            r['symbol'], pri, r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], ', '.join(r['tags'])))
    if len(watches) > 10:
        print('  ...+%d more' % (len(watches) - 10))
else:
    print('  無 WATCH 訊號')

print('\n' + '='*60)
print('SUMMARY')
if buys:
    print('BUY: %s' % ', '.join(r['symbol'] for r in buys))
if watches:
    print('WATCH: %s' % ', '.join(r['symbol'] for r in watches[:5]))