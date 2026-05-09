import sqlite3
conn = sqlite3.connect('data/yfinance.db')
c = conn.cursor()
c.execute("SELECT symbol FROM daily_ohlcv GROUP BY symbol ORDER BY symbol LIMIT 50")
rows = c.fetchall()
for r in rows:
    print(r[0])
conn.close()