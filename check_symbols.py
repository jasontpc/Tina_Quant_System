# -*- coding: utf-8 -*-
"""Check symbols table structure"""
import sqlite3
from pathlib import Path

DB = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yfinance.db')
conn = sqlite3.connect(str(DB))
cur = conn.cursor()

cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='symbols'")
schema = cur.fetchone()[0]
print('symbols schema:', schema)

cur.execute('SELECT COUNT(*) FROM symbols')
print('count:', cur.fetchone()[0])

# List a few
cur.execute('SELECT symbol, universe_group FROM symbols LIMIT 5')
for r in cur.fetchall():
    print(' ', r)

conn.close()