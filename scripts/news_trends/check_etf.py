# -*- coding: utf-8 -*-
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\etf.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check if 0050, 00631L, 00981A exist
symbols = ['0050.TW', '00631L.TW', '00981A.TW']
for sym in symbols:
    cur.execute('SELECT symbol, name, updated_at FROM etf_info WHERE symbol=?', (sym,))
    row = cur.fetchone()
    if row:
        print(f"EXISTS: {row}")
    else:
        print(f"MISSING: {sym}")

# Also check latest price in etf_daily
for sym in symbols:
    cur.execute('SELECT MAX(date), close FROM etf_daily WHERE symbol=?', (sym,))
    row = cur.fetchone()
    print(f"{sym} latest: date={row[0]}, close={row[1]}")

conn.close()
print("[OK]")