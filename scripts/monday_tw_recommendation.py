import sqlite3, json
from pathlib import Path
from datetime import datetime

DB = Path('data/yfinance.db')

# Load optimized strategies
with open('data/optimized_stock_strategies.json', 'r', encoding='utf-8') as f:
    opt_strategies = json.load(f)

# Load team watch list
with open('data/team_watch_list.json', 'r', encoding='utf-8') as f:
    watchlist = json.load(f)

conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60, volume
    FROM daily_ohlcv WHERE symbol LIKE '%.TW' OR symbol LIKE '%.TWO'
    ORDER BY symbol, date DESC
""")
rows = c.fetchall()
conn.close()

symbols = {}
for r in rows:
    sym = r[0]
    if sym not in symbols:
        symbols[sym] = r

# Strategy parameters
STRAT_PARAMS = {
    'MEAN_REVERSION': {'rsi_min': 25, 'rsi_max': 50, 'macd_req': False, 'ma_req': False, 'sl': 1.5, 'tp': 3.0},
    'STRONG_UPTREND': {'rsi_min': 40, 'rsi_max': 70, 'macd_req': True, 'ma_req': True, 'sl': 2.0, 'tp': 4.0},
    'MIXED': {'rsi_min': 35, 'rsi_max': 55, 'macd_req': True, 'ma_req': True, 'sl': 1.5, 'tp': 3.0},
    'RANGE_BOUND': {'rsi_min': 30, 'rsi_max': 60, 'macd_req': False, 'ma_req': False, 'sl': 1.0, 'tp': 2.5},
}

results = []
for team, info in watchlist['teams'].items():
    for sym in info['watch_list']:
        if sym not in symbols:
            continue

        r = symbols[sym]
        price = r[2]
        rsi = r[3] or 50
        macd = r[4] or 0
        sma20 = r[5] or price
        sma60 = r[6] or price

        opt = opt_strategies.get(sym, {})
        strat_name = opt.get('best_strategy', 'MIXED')
        strat_params = STRAT_PARAMS.get(strat_name, STRAT_PARAMS['MIXED'])

        # Score based on strategy fit
        score = 0
        tags = []

        # RSI fit
        rsi_min = strat_params['rsi_min']
        rsi_max = strat_params['rsi_max']
        if rsi_min <= rsi <= rsi_max:
            score += 30
            tags.append('RSI_FIT')
        elif rsi < rsi_min:
            score += 15; tags.append('RSI_LOW')
        else:
            continue  # Skip overbought

        # MACD fit
        if strat_params['macd_req']:
            if macd > 0:
                score += 25; tags.append('MACD_BULL')
            elif macd > -0.3:
                score += 10; tags.append('MACD_ZERO')
            else:
                continue  # MACD required but negative

        # MA fit
        if strat_params['ma_req']:
            if sma20 > sma60:
                score += 15; tags.append('MA_BULL')

        # Strategy tag
        tags.append(strat_name)

        results.append({
            'symbol': sym,
            'team': team,
            'price': price,
            'rsi': round(rsi, 1),
            'macd': round(macd, 4),
            'sma20': round(sma20, 2),
            'sma60': round(sma60, 2),
            'score': score,
            'tags': tags,
            'strategy': strat_name,
            'wr': opt.get('wr', 0),
            'trades': opt.get('trades', 0)
        })

# Sort by score
results.sort(key=lambda x: x['score'], reverse=True)

print('='*70)
print('  Tina 明日台股建議（2026-05-04 週一）')
print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
print('='*70)
print()

# Filter out stocks with score < 40 (no signal)
buys = [r for r in results if r['score'] >= 60]
watches = [r for r in results if 40 <= r['score'] < 60]

print('[BUY Signal] Score >= 60')
print('%-10s %6s %5s %7s %5s %-12s %s' % ('代號', '價格', 'RSI', 'MACD', 'Score', '策略', '標籤'))
print('-'*70)
for r in buys:
    rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
    macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
    print('%s %8.2f %s(%.1f) %s(%.3f) %d %-12s %s' % (
        r['symbol'], r['price'], rsi_flag, r['rsi'],
        macd_flag, r['macd'], r['score'], r['strategy'], ', '.join(r['tags'])))

print()
print('[WATCH] Score 40-59')
print('%-10s %6s %5s %7s %5s %-12s %s' % ('代號', '價格', 'RSI', 'MACD', 'Score', '策略', '標籤'))
print('-'*70)
for r in watches[:10]:
    rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
    macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
    print('%s %8.2f %s(%.1f) %s(%.3f) %d %-12s %s' % (
        r['symbol'], r['price'], rsi_flag, r['rsi'],
        macd_flag, r['macd'], r['score'], r['strategy'], ', '.join(r['tags'])))

print()
print('='*70)
print('[Market Notes - 2026-05-03]')
print()
print('  TWII 上週 +17.3%，動能強勁')
print('  記憶體族群（2344/2408）今天大跌，不建議接')
print('  2382.TW 廣達，觀察 $310 支撐')
print('  2881.TW 富邦金，MACD 已翻正')
print()
print('[Summary]')
if buys:
    print('BUY: %s' % ', '.join(r['symbol'] for r in buys))
if watches:
    print('WATCH: %s' % ', '.join(r['symbol'] for r in watches[:5]))