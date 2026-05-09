import sqlite3, sys
from pathlib import Path

DB_PATH = Path('data/yfinance.db')
conn = sqlite3.connect(str(DB_PATH))
c = conn.cursor()

# Check 2330.TW data
c.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM daily_ohlcv WHERE symbol='2330.TW'")
count, mn, mx = c.fetchone()
print(f'2330.TW: {count} rows, {mn} to {mx}')

# Check column names
c.execute("PRAGMA table_info(daily_ohlcv)")
cols = [r[1] for r in c.fetchall()]
print('Columns:', cols)

# Test query
c.execute("SELECT date, close, rsi_14, sma_20, sma_60 FROM daily_ohlcv WHERE symbol='2330.TW' AND date >= '2024-01-01' AND date <= '2026-05-08' ORDER BY date LIMIT 5")
for row in c.fetchall():
    print(row)

conn.close()