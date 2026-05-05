# -*- coding: utf-8 -*-
import sqlite3, os
conn = sqlite3.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel.db')
cur = conn.cursor()

cur.execute('SELECT MIN(date), MAX(date), COUNT(*) FROM futures_daily WHERE futures_id="TX"')
min_d, max_d, cnt = cur.fetchone()
print(f'TX Range: {min_d} to {max_d} ({cnt} records)')

size = os.path.getsize(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel.db') / 1024
print(f'vogel.db: {size:.1f} KB')

cur.execute('SELECT date, close, rsi, atr, bb_upper, bb_middle, bb_lower FROM futures_daily WHERE futures_id="TX" ORDER BY date DESC LIMIT 10')
rows = cur.fetchall()
print('Latest 10:')
for r in rows:
    print(f'  {r}')

conn.close()