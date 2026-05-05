import sqlite3, json
from pathlib import Path
from datetime import datetime

DB = Path('data/yfinance.db')

# Load optimized strategies
with open('data/optimized_stock_strategies.json', 'r', encoding='utf-8') as f:
    opt_strategies = json.load(f)

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

# Strategy params
STRAT_PARAMS = {
    'MEAN_REVERSION': {'rsi_min': 25, 'rsi_max': 50, 'macd_req': False, 'ma_req': False, 'sl': 1.5, 'tp': 3.0},
    'STRONG_UPTREND': {'rsi_min': 40, 'rsi_max': 70, 'macd_req': True, 'ma_req': True, 'sl': 2.0, 'tp': 4.0},
    'MIXED': {'rsi_min': 35, 'rsi_max': 55, 'macd_req': True, 'ma_req': True, 'sl': 1.5, 'tp': 3.0},
    'RANGE_BOUND': {'rsi_min': 30, 'rsi_max': 60, 'macd_req': False, 'ma_req': False, 'sl': 1.0, 'tp': 2.5},
}

# US stock watch list
US_STOCKS = ['MSFT', 'CRM', 'NVDA', 'AMD', 'AVGO', 'GOOGL', 'META', 'AMZN', 'NFLX', 'ADBE', 'PYPL', 'SNOW', 'PLTR', 'COIN', 'D', 'SO', 'VTI']

results = []
for sym in US_STOCKS:
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

    score = 0
    tags = []

    # RSI fit
    if strat_params['rsi_min'] <= rsi <= strat_params['rsi_max']:
        score += 30; tags.append('RSI_FIT')
    elif rsi < strat_params['rsi_min']:
        score += 15; tags.append('RSI_LOW')
    else:
        continue

    # MACD fit
    if strat_params['macd_req']:
        if macd > 0:
            score += 25; tags.append('MACD_BULL')
        elif macd > -0.3:
            score += 10; tags.append('MACD_ZERO')
        else:
            continue

    # MA fit
    if strat_params['ma_req']:
        if sma20 > sma60:
            score += 15; tags.append('MA_BULL')

    tags.append(strat_name)

    results.append({
        'symbol': sym,
        'price': price,
        'rsi': round(rsi, 1),
        'macd': round(macd, 4),
        'score': score,
        'tags': tags,
        'strategy': strat_name,
        'wr': opt.get('wr', 0),
        'trades': opt.get('trades', 0)
    })

results.sort(key=lambda x: x['score'], reverse=True)

print('='*65)
print('  Tina 明日美股操作建議（2026-05-04 週一）')
print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
print('='*65)
print()

buys = [r for r in results if r['score'] >= 60]
watches = [r for r in results if 40 <= r['score'] < 60]

print('[BUY Signal] Score >= 60')
if buys:
    print('%-10s %9s %5s %8s %5s %-12s %s' % ('Symbol', 'Price', 'RSI', 'MACD', 'Score', 'Strategy', 'Tags'))
    print('-'*65)
    for r in buys:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        print('%s %10.2f %s(%.1f) %s(%.3f) %d %-12s %s' % (
            r['symbol'], r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], r['strategy'], ', '.join(r['tags'])))
else:
    print('  None')

print()
print('[WATCH] Score 40-59')
if watches:
    print('%-10s %9s %5s %8s %5s %-12s %s' % ('Symbol', 'Price', 'RSI', 'MACD', 'Score', 'Strategy', 'Tags'))
    print('-'*65)
    for r in watches:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        print('%s %10.2f %s(%.1f) %s(%.3f) %d %-12s %s' % (
            r['symbol'], r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], r['strategy'], ', '.join(r['tags'])))
else:
    print('  None')

print()
print('='*65)
print('[Summary]')
if buys:
    print('BUY: %s' % ', '.join(r['symbol'] for r in buys))
if watches:
    print('WATCH: %s' % ', '.join(r['symbol'] for r in watches))