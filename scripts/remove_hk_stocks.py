# -*- coding: utf-8 -*-
"""Remove HK stocks from yfinance.db"""
import sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/yfinance.db')
c = conn.cursor()

# Count HK rows
c.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE symbol LIKE '%.HK'")
hk_rows = c.fetchone()[0]
print(f"HK rows to delete: {hk_rows}")

# Get HK symbols
c.execute("SELECT DISTINCT symbol FROM daily_ohlcv WHERE symbol LIKE '%.HK'")
hk_syms = [r[0] for r in c.fetchall()]
print(f"HK symbols ({len(hk_syms)}): {hk_syms}")

# Delete HK rows
c.execute("DELETE FROM daily_ohlcv WHERE symbol LIKE '%.HK'")
deleted = c.rowcount
conn.commit()
print(f"Deleted: {deleted} rows")

conn.close()
print("Done")