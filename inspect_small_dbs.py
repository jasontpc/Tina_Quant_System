# -*- coding: utf-8 -*-
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')
data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
for db_name in ['nana_stocks.db', 'leo_stocks.db']:
    db_path = os.path.join(data_dir, db_name)
    print('='*50)
    print(db_name)
    print('='*50)
    if not os.path.exists(db_path):
        print('NOT FOUND'); continue
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (t,) in cur.fetchall():
        cnt = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
        sample = cur.execute(f'SELECT * FROM "{t}" LIMIT 2').fetchall()
        print(f'Table: {t} | Rows: {cnt:,} | Cols: {cols}')
        if sample: print(f'  Sample[0]: {sample[0]}')
    conn.close()