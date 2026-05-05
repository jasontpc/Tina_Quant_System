# -*- coding: utf-8 -*-
"""Check existing database schemas"""
import sqlite3
import os

base = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"

dbs = {
    "master_backtest": os.path.join(base, "data", "master_backtest.db"),
    "tw_etf": os.path.join(base, "tw_etf", "tw_etf.db"),
    "us_etf": os.path.join(base, "us_etf", "us_etf.db"),
    "etf_return": os.path.join(base, "tw_etf_return", "tw_etf_return.db"),
    "us_etf_return": os.path.join(base, "us_etf_return", "us_etf_return.db"),
}

for name, path in dbs.items():
    print(f"\n=== {name} ===")
    if not os.path.exists(path):
        print(f"  [X] Not found")
        continue
    
    size_kb = os.path.getsize(path) / 1024
    print(f"  Size: {size_kb:.1f} KB")
    
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    print(f"  Tables: {tables}")
    
    for t in tables[:5]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            cur.execute(f"PRAGMA table_info({t})")
            cols = [c[1] for c in cur.fetchall()]
            print(f"    {t}: {count} rows, cols={cols}")
        except Exception as e:
            print(f"    {t}: error - {e}")
    
    conn.close()