# -*- coding: utf-8 -*-
import sqlite3

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_history.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("SELECT symbol, name FROM stocks ORDER BY symbol")
all_stocks = cur.fetchall()
print("All stocks in DB:")
for s, n in all_stocks:
    print(f"  {s} {n}")

# Check if 2330 exists
cur.execute("SELECT COUNT(*) FROM stocks WHERE symbol='2330'")
print(f"\n2330 in stocks: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE symbol='2330'")
print(f"2330 in daily_ohlcv: {cur.fetchone()[0]}")

conn.close()