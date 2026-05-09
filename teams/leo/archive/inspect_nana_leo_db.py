# -*- coding: utf-8 -*-
import sqlite3, os

data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

for db_name in ['nana_stocks.db', 'leo_stocks.db']:
    db_path = os.path.join(data_dir, db_name)
    print(f"\n{'='*60}")
    print(f"🔍 {db_name}")
    print('='*60)
    if not os.path.exists(db_path):
        print("  NOT FOUND"); continue
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    for (t,) in tables:
        cols = cur.execute(f"PRAGMA table_info(\"{t}\")").fetchall()
        cnt = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        sample = cur.execute(f'SELECT * FROM "{t}" LIMIT 3').fetchall()
        print(f"\n  📋 Table: {t}")
        print(f"     Rows: {cnt:,}")
        print(f"     Columns: {[c[1] for c in cols]}")
        if sample:
            print(f"     Sample (row 1): {sample[0]}")
    conn.close()