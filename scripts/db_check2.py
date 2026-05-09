import sqlite3
conn = sqlite3.connect('../data/yfinance.db')
c = conn.cursor()
c.execute("PRAGMA table_info(daily_ohlcv)")
print("Columns:", c.fetchall())
conn.close()