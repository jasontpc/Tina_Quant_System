# -*- coding: utf-8 -*-
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

# Get RSI from tw_history
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_history.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

# Get RSI for Nana candidates
symbols = ['2330', '2454', '2303', '2317', '3034', '2382', '3665', '2376', '2354']

for sym in symbols:
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%{sym}%'")
    rows = cur.fetchall()
    print(f'{sym}: {[r[0] for r in rows]}')

conn.close()