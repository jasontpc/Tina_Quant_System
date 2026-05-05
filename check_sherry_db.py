import sqlite3, os
data = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
for f in os.listdir(data):
    if 'sherry' in f.lower() and f.endswith('.db'):
        print(f)
        conn = sqlite3.connect(data + '\\' + f)
        cur = conn.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        for t in tables:
            print(f'  {t[0]}')
            cols = cur.execute(f'PRAGMA table_info({t[0]})').fetchall()
            print(f'    cols: {[c[1] for c in cols]}')
        conn.close()