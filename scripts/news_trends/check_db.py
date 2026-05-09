# -*- coding: utf-8 -*-
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\etf.db'
try:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols = [r[1] for r in cur.fetchall()]
        print(f"  {t}: {cols}")
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"    Rows: {cur.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
print("[OK]")