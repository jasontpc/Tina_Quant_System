# -*- coding: utf-8 -*-
import sqlite3

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_history.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check 2330 latest data
cur.execute("SELECT date, close FROM daily_ohlcv WHERE symbol='2330' ORDER BY date DESC LIMIT 5")
print("2330 latest:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Check 2382 latest data
cur.execute("SELECT date, close FROM daily_ohlcv WHERE symbol='2382' ORDER BY date DESC LIMIT 5")
print("\n2382 latest:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Check count on 2026-04-30
cur.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE date='2026-04-30'")
print(f"\nRecords on 2026-04-30: {cur.fetchone()[0]}")

# Check SPY latest
db2 = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_history.db'
conn2 = sqlite3.connect(db2)
cur2 = conn2.cursor()
cur2.execute("SELECT date, close FROM daily_ohlcv WHERE symbol='SPY' ORDER BY date DESC LIMIT 3")
print("\nSPY latest:")
for r in cur2.fetchall():
    print(f"  {r[0]}: {r[1]}")
conn2.close()

conn.close()
print("\n=== Data verification complete ===")