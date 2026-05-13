# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== positions_log 驗證 ===')
c.execute("SELECT id, symbol, entry_price, current_price, stop_loss, target_price, status, pnl_pct, days_held FROM positions_log")
for r in c.fetchall():
    print(f'  id={r[0]} {r[1]}: entry={r[2]} cur={r[3]} stop={r[4]} target={r[5]} status={r[6]} pnl={r[7]} days={r[8]}')

conn.close()