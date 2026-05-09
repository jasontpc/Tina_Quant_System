import sqlite3
from pathlib import Path

db = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_margin.db')
conn = sqlite3.connect(str(db))
cur = conn.cursor()

print('=== TW Margin DB 現況 ===')

# Check all tables
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
print()

# Check for any recent data (2026-05)
for t in tables:
    name = t[0]
    try:
        latest = cur.execute(f'SELECT MAX(date) FROM "{name}"').fetchone()[0]
        count = cur.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        print(f'{name}: {count} rows, latest: {latest}')
    except Exception as e:
        print(f'{name}: Error - {e}')

# Check margin_daily structure
print()
print('=== margin_daily 結構 ===')
cols = cur.execute("PRAGMA table_info(margin_daily)").fetchall()
print([c[1] for c in cols])

# Check if fetch_margin_finmind saved to a different table
print()
print('=== 查找2026-05資料 ===')
for t in tables:
    name = t[0]
    try:
        may_data = cur.execute(f'SELECT COUNT(*) FROM "{name}" WHERE date >= "2026-05-01"').fetchone()[0]
        if may_data > 0:
            print(f'{name}: {may_data} rows in May 2026')
    except:
        pass

conn.close()