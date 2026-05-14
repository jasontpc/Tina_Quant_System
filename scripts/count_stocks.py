import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

dbs = [
    ('TW', r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_history.db'),
    ('US', r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_history.db'),
]

for name, db in dbs:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f'{name}: tables = {tables}')
    for t in tables:
        try:
            cur.execute(f"SELECT count(*) FROM {t}")
            n = cur.fetchone()[0]
            print(f'  {t}: {n} rows')
        except Exception as e:
            print(f'  {t}: error - {e}')
    conn.close()