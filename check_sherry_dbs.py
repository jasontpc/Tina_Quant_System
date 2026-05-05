import os, sqlite3

print('=== Sherry 資料庫狀態 ===\n')

dbs = [
    ('sherry_etf.db', 'ETF即時數據'),
    ('sherry_backtest.db', 'DCA回測數據'),
    ('sherry_sim_trades.db', '模擬交易數據'),
]

for db_name, desc in dbs:
    path = 'C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\data\\' + db_name
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        table_counts = {}
        for t in tables:
            try:
                cnt = cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                table_counts[t] = cnt
            except:
                pass
        print(f'{db_name} ({desc})')
        print(f'  大小: {size:.0f} KB')
        for t, cnt in table_counts.items():
            print(f'  {t}: {cnt:,}筆')
        print()
        conn.close()
    else:
        print(f'{db_name}: NOT FOUND')