import os
import sqlite3
from datetime import datetime

print('=== FULL SYSTEM AUDIT REPORT ===')
print('Time:', datetime.now().strftime('%Y-%m-%d %H:%M'))
print()

# 1. Database Status
print('--- DATABASE STATUS ---')
dbs = [
    'data/leverage_etf.db',
    'data/us_history.db',
    'data/us_value_growth.db',
    'data/macro_institutional.db',
    'data/financial_history.db'
]
for db in dbs:
    if os.path.exists(db):
        size = os.path.getsize(db) / 1024 / 1024
        mtime = datetime.fromtimestamp(os.path.getmtime(db))
        age = (datetime.now() - mtime).total_seconds() / 3600
        status = 'STALE' if age > 12 else 'OK'
        print(f'{db}: {size:.1f}MB, updated {age:.1f}h [{status}]')
    else:
        print(f'{db}: NOT FOUND')

# Check trade_history
print()
if os.path.exists('data/trade_history.db'):
    print('trade_history.db: FOUND')
else:
    print('trade_history.db: NOT FOUND (needs to be created)')

# Check unified_trading
print()
if os.path.exists('data/unified_db/unified_trading.db'):
    size = os.path.getsize('data/unified_db/unified_trading.db') / 1024
    print(f'unified_trading.db: FOUND ({size:.0f}KB)')
else:
    print('unified_trading.db: NOT FOUND')

# 2. Data Tables
print()
print('--- US HISTORY DB TABLES ---')
try:
    conn = sqlite3.connect('data/us_history.db')
    c = conn.cursor()
    c.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = [r[0] for r in c.fetchall()]
    for t in tables[:5]:
        try:
            c.execute(f'SELECT COUNT(*) FROM {t}')
            count = c.fetchone()[0]
            c.execute(f'SELECT MAX(date) FROM {t}')
            last = c.fetchone()[0]
            print(f'{t}: {count} rows, last: {last}')
        except:
            print(f'{t}: error')
    conn.close()
except:
    print('Cannot read us_history.db')

# 3. Stock Strategies
print()
print('--- STOCK STRATEGIES ---')
sd = 'configs/stock_strategies'
if os.path.exists(sd):
    files = os.listdir(sd)
    tw = [f for f in files if f.replace('.json','').isdigit()]
    us = [f for f in files if not f.replace('.json','').isdigit()]
    print(f'Total: {len(files)} strategies (TW: {len(tw)}, US: {len(us)})')
else:
    print('Stock strategies directory not found')

# 4. Watchlist JSON
print()
print('--- WATCHLIST JSON ---')
watchlists = ['nana_watchlist.json', 'leo_watchlist.json', 'ray_watchlist.json', 'maggy_watchlist.json', 'market_regime.json']
for wl in watchlists:
    path = f'data/{wl}'
    if os.path.exists(path):
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        age = (datetime.now() - mtime).total_seconds() / 3600
        status = 'STALE' if age > 12 else 'OK'
        print(f'{wl}: {age:.1f}h [{status}]')
    else:
        print(f'{wl}: NOT FOUND')

# 5. Missing Items
print()
print('=== ITEMS TO CREATE/UPDATE ===')
missing = []
if not os.path.exists('data/trade_history.db'):
    missing.append('trade_history.db (historical trade data)')
print(f'Missing: {len(missing)} items')
for m in missing:
    print(f'  - {m}')

print()
print('=== AUDIT COMPLETE ===')