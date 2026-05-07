# -*- coding: utf-8 -*-
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')
data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
conn = sqlite3.connect(os.path.join(data_dir, 'tw_margin.db'))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
for (t,) in cur.fetchall():
    cnt = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"Table: {t} | {cnt:,} rows")
    try:
        # try date-like columns
        cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
        date_cols = [c for c in cols if 'date' in c.lower() or 'trade' in c.lower()]
        if date_cols:
            latest = cur.execute(f'SELECT MAX("{date_cols[0]}") FROM "{t}"').fetchone()[0]
            print(f"  Latest date col [{date_cols[0]}]: {latest}")
    except: pass
conn.close()