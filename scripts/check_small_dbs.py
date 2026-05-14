import sqlite3, os

small_dbs = [
    r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\limitup.db',
    r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\reddit_sentiment.db',
    r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\stocktwits_sentiment.db',
    r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stocks.db',
]

for db in small_dbs:
    size = os.path.getsize(db)
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tnames = [r[0] for r in cur.fetchall()]
    total_rows = 0
    for t in tnames:
        try:
            cur.execute(f"SELECT count(*) FROM {t}")
            total_rows += cur.fetchone()[0]
        except:
            pass
    print(f'{os.path.basename(db)}: {size} bytes, {len(tnames)} tables, {total_rows} rows')
    conn.close()