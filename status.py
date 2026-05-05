import sqlite3
conn = sqlite3.connect('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv')
n = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM daily_ohlcv')
rows = cur.fetchone()[0]
conn.close()
print(f'Symbols: {n}')
print(f'Rows: {rows:,}')
print(f'Added: ~{n-160}')