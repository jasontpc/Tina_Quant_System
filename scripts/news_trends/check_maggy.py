# -*- coding: utf-8 -*-
import sqlite3
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yfinance.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

# Check a sample
for t in tables[:5]:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    print(f"  {t}: {cols}")
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    print(f"    Rows: {cnt}")

data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
for f in ['maggy.db', 'maggy_sim_trades.db', 'sherry_etf.db', 'sherry_backtest.db']:
    path = os.path.join(data_dir, f)
    print(f'{f}: exists={os.path.exists(path)}, size={os.path.getsize(path) if os.path.exists(path) else 0}')

conn.close()
print('[OK]')