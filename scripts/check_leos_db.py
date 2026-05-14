import sqlite3, os
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\portfolio\leos_portfolio.db'
if not os.path.exists(db):
    print('DB not found:', db)
else:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    print('Tables:', tables)
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f'  {t}: {cur.fetchone()[0]} rows')
    conn.close()