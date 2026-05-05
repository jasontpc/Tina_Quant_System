import sqlite3
from pathlib import Path

conn = sqlite3.connect('data/positions.db')
c = conn.cursor()

# Check if positions table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)

# Create positions table if not exists
if 'positions' not in tables:
    c.execute('''CREATE TABLE positions (symbol TEXT, name TEXT, qty INTEGER, avg_price REAL, updated TEXT)''')
    conn.commit()

# Update or insert 00713
c.execute('''INSERT OR REPLACE INTO positions (symbol, name, qty, avg_price, updated) VALUES (?, ?, ?, ?, ?)''', 
    ('00713.TW', '元大高息低波', 300, 53.22, '2026-05-03'))
conn.commit()

# Verify
c.execute('SELECT * FROM positions WHERE symbol=?', ('00713.TW',))
row = c.fetchone()
print('\n00713.TW Position:')
print('  Symbol:', row[0])
print('  Name:', row[1])
print('  Qty:', row[2])
print('  Avg Price: $%.2f' % row[3])
print('  Updated:', row[4])

# Also update 2382.TW if exists
c.execute('SELECT * FROM positions WHERE symbol=?', ('2382.TW',))
row2 = c.fetchone()
if row2:
    print('\n2382.TW Position:')
    print('  Symbol:', row2[0])
    print('  Qty:', row2[2])
    print('  Avg Price: $%.2f' % row2[3])

conn.close()
print('\nDone')