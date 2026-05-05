import sqlite3, os

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy_sim_trades.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print('Tables:', [t[0] for t in tables])
    for t in tables:
        try:
            cnt = cur.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
            cols = [c[1] for c in cur.execute(f'PRAGMA table_info({t[0]})').fetchall()]
            print(f'  {t[0]}: {cnt} rows, cols: {cols}')
        except Exception as e:
            print(f'  {t[0]}: {e}')
    conn.close()
else:
    print('DB not found')