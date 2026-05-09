# Check yfinance symbols and US coverage
import sqlite3
from pathlib import Path

BASE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data')
conn = sqlite3.connect(str(BASE / 'yfinance.db'))
cur = conn.cursor()

# Check symbols table
cur.execute("SELECT * FROM symbols LIMIT 10")
rows = cur.fetchall()
cur.execute("PRAGMA table_info(symbols)")
cols = [r[1] for r in cur.fetchall()]
print('Symbols columns:', cols)
print('Sample rows:')
for r in rows:
    print(dict(zip(cols, r)))

# Count TW vs US symbols
cur.execute("SELECT COUNT(*) FROM symbols WHERE symbol LIKE '%.TW' OR symbol LIKE '%TWO'")
tw_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM symbols WHERE symbol NOT LIKE '%.TW' AND symbol NOT LIKE '%TWO'")
us_count = cur.fetchone()[0]
print(f'\nTW symbols: {tw_count}')
print(f'US symbols: {us_count}')

conn.close()
