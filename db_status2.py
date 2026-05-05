import sqlite3, os
data = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
print('=== Tina 全系統資料庫狀態（22:23）===')
print()
dbs = [
    ('tw_history.db', '台股歷史'),
    ('us_history.db', '美股歷史'),
    ('maggy_ai_tech.db', 'Maggy AI/科技'),
    ('sherry_etf.db', 'Sherry ETF'),
    ('us_sim_trades.db', '美股模擬交易'),
    ('master_backtest.db', '主回測資料庫'),
    ('vogel_indicators.db', 'Vogel 台指'),
]
total_size = 0
for db, desc in dbs:
    p = data + '\\' + db
    if os.path.exists(p):
        sz = os.path.getsize(p) / 1024
        total_size += sz
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        try:
            tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            total = 0
            for t in tables:
                try:
                    total += cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                except: pass
            print(f'{desc:<18} {sz:>7.0f}KB  {total:>10,}筆記錄')
        except: print(f'{desc:<18} {sz:>7.0f}KB  ERROR')
        conn.close()
print()
print(f'總大小: {total_size:.0f} KB ({total_size/1024:.1f} MB)')