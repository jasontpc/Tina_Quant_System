# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT MIN(timestamp), MAX(timestamp) FROM signals_log WHERE approved=0")
r = c.fetchone()
print(f'approved=0 range: {r[0]} ~ {r[1]}')
conn.close()