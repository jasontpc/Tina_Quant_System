import sqlite3, os

empty_dbs = ['leo_stocks.db','nana_stocks.db','maggy.db','limitup.db','rsi.db','tina_trading.db']

for db_name in empty_dbs:
    path = f'data/{db_name}'
    size = os.path.getsize(path) if os.path.exists(path) else -1
    print(f'\n=== {db_name} ({size:,} bytes) ===')
    try:
        conn = sqlite3.connect(path)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            print('  (no tables)')
        for t in tables:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f'  {t}: {cnt} rows')
        conn.close()
    except Exception as e:
        print(f'  ERROR: {e}')