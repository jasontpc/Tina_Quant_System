# -*- coding: utf-8 -*-
import sqlite3
import os

base = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"

dbs = {
    "tw_history": os.path.join(base, "data", "tw_history.db"),
    "us_history": os.path.join(base, "data", "us_history.db"),
}

for name, path in dbs.items():
    print(f"\n=== {name} ===")
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        print("Tables:", tables)
        for t in tables:
            cur.execute(f"PRAGMA table_info({t})")
            cols = [c[1] for c in cur.fetchall()]
            print(f"  {t}: {cols}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")