# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel.db')
cur = conn.cursor()
cur.execute('SELECT date, close, rsi, atr FROM futures_daily WHERE futures_id="TX" ORDER BY date DESC LIMIT 10')
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()

# Check for zero atr
cur2 = conn.cursor()
cur2.execute('SELECT COUNT(*) FROM futures_daily WHERE futures_id="TX" AND (atr IS NULL OR atr=0)')
print('\nZero/NULL ATR records:', cur2.fetchone()[0])