# -*- coding: utf-8 -*-
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')
data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
conn = sqlite3.connect(os.path.join(data_dir, 'tina_trading.db'))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables:", [r[0] for r in tables])
for (t,) in tables:
    cnt = cur.execute(f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0]
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info(\"{t}\")").fetchall()]
    print(f"  {t}: {cnt} rows | Cols: {cols}")
conn.close()