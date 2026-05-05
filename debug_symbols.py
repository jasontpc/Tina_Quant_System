# -*- coding: utf-8 -*-
import sqlite3

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_history.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check what symbols exist for 2330, 2382, 2454
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv WHERE symbol IN ('2330','2382','2454')")
print("Symbols found:", [r[0] for r in cur.fetchall()])

# Check all distinct symbols
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
print("Total distinct symbols:", cur.fetchone()[0])

# Check symbol patterns
cur.execute("SELECT symbol FROM daily_ohlcv WHERE symbol LIKE '%2330%' LIMIT 5")
print("2330-like symbols:", [r[0] for r in cur.fetchall()])

# Check for 2330 in various formats
cur.execute("SELECT symbol, COUNT(*) FROM daily_ohlcv GROUP BY symbol LIMIT 10")
print("First 10 symbols:", cur.fetchall())

conn.close()