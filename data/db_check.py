import sqlite3
conn = sqlite3.connect('data/yfinance.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
for t in tables:
    c.execute(f"SELECT * FROM {t} LIMIT 1")
    cols = [d[0] for d in c.description]
    print(t, ':', cols)
c.execute('SELECT COUNT(*) FROM daily_ohlcv')
print('total rows:', c.fetchone()[0])
c.execute('SELECT MIN(date), MAX(date) FROM daily_ohlcv')
print('date range:', c.fetchone())
c.execute('SELECT symbol FROM daily_ohlcv GROUP BY symbol LIMIT 20')
print('sample symbols:', [r[0] for r in c.fetchall()])
conn.close()