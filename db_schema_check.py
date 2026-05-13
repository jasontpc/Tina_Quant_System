# -*- coding: utf-8 -*-
import sqlite3
db = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("PRAGMA table_info(positions_log)")
for r in c.fetchall():
    print(r)
conn.close()