# Check universe coverage
import sqlite3, os, sys
from pathlib import Path

BASE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data')

dbs = {
    'tw_stock_registry': BASE / 'tw_stock_registry.db',
    'yfinance': BASE / 'yfinance.db',
    'us_history': BASE / 'us_history.db',
}

for name, path in dbs.items():
    if not path.exists():
        print(f'{name}: NOT FOUND')
        continue
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f'\n=== {name} === ({path.stat().st_size:,} bytes)')
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            cnt = cur.fetchone()[0]
            print(f'  {t}: {cnt:,} rows')
        conn.close()
    except Exception as e:
        print(f'{name}: Error - {e}')
