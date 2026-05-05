# -*- coding: utf-8 -*-
"""Check main database status"""
import sqlite3
import os

base = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"

dbs = {
    "TW History": os.path.join(base, "data", "tw_history.db"),
    "US History": os.path.join(base, "data", "us_history.db"),
    "ETF History": os.path.join(base, "data", "etf_history.db"),
    "Fugle": os.path.join(base, "data", "fugle.db"),
}

print("=== Database Status Check ===\n")

for name, path in dbs.items():
    if not os.path.exists(path):
        print(f"[X] {name}: File not found")
        continue

    size_kb = os.path.getsize(path) / 1024
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]

        print(f"[OK] {name} ({size_kb:.1f} KB)")
        print(f"    Tables: {tables}")

        for t in tables[:5]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                print(f"    - {t}: {count} rows")
            except:
                pass

        # Check latest date
        for t in tables:
            try:
                cur.execute(f"PRAGMA table_info({t})")
                cols = [c[1] for c in cur.fetchall()]
                col_str = ','.join(cols).lower()
                if 'date' in col_str:
                    cur.execute(f"SELECT MAX(date) FROM {t}")
                    last = cur.fetchone()[0]
                    if last:
                        print(f"    Latest date in {t}: {last}")
            except:
                pass

        print()
    except Exception as e:
        print(f"[X] {name}: {e}")
    finally:
        conn.close()

print("=== Done ===")