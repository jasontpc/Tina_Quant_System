import sqlite3, os
db_path = 'data/us_history.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print('tables:', tables)
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    print(f'{t}: {cols}')
    # Check if there's a technicals-like table
    if any('atr' in c.lower() for c in cols):
        print(f'  -> atr found in {t}')
conn.close()

# Also check the actual error: "atr_14 column missing"
# This likely comes from scripts that compute atr_14 but the column isn't there
# Let's add it to whatever table has high/low/close
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    col_names = [c.lower() for c in cols]
    if 'high' in col_names and 'low' in col_names and 'atr_14' not in col_names:
        try:
            conn2 = sqlite3.connect(db_path)
            cur2 = conn2.cursor()
            cur2.execute(f"ALTER TABLE {t} ADD COLUMN atr_14 REAL")
            conn2.commit()
            conn2.close()
            print(f'Added atr_14 to {t}')
        except Exception as e:
            print(f'ALTER {t}: {e}')
conn.close()