import sqlite3
conn = sqlite3.connect('data/yfinance.db')
c = conn.cursor()

c.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv WHERE date >= '2020-01-01' AND close IS NOT NULL AND close > 0 AND volume > 0 AND symbol LIKE '%.TW'")
tw = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv WHERE date >= '2020-01-01' AND close IS NOT NULL AND close > 0 AND volume > 0 AND symbol NOT LIKE '%.TW' AND symbol NOT LIKE '%.TWO'")
us = c.fetchone()[0]

print(f'TW symbols: {tw}')
print(f'US symbols: {us}')

# Sample 20 TW symbols
c.execute("SELECT DISTINCT symbol FROM daily_ohlcv WHERE date >= '2020-01-01' AND close IS NOT NULL AND close > 0 AND volume > 0 AND symbol LIKE '%.TW' ORDER BY symbol LIMIT 50 OFFSET 20")
print('TW sample:', [r[0] for r in c.fetchall()])

conn.close()