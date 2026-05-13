import sqlite3
conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    cnt = c.execute(f'SELECT count(*) FROM "{t[0]}"').fetchone()[0]
    print(f'  {t[0]}: {cnt} rows')

# Check schema for signals_log
print('\n--- signals_log schema ---')
try:
    cols = c.execute("PRAGMA table_info(signals_log)").fetchall()
    print([col[1] for col in cols])
except Exception as e:
    print(e)

# Recent signals
print('\n--- Recent signals (10) ---')
try:
    rows = c.execute('SELECT * FROM signals_log ORDER BY ROWID DESC LIMIT 10').fetchall()
    for r in rows: print(r)
except Exception as e:
    print(e)

# Backtest reports stats
print('\n--- backtest_reports ---')
try:
    cnt = c.execute('SELECT count(*) FROM backtest_reports').fetchone()[0]
    avg_sharpe = c.execute('SELECT avg(sharpe_ratio) FROM backtest_reports').fetchone()[0]
    max_sharpe = c.execute('SELECT max(sharpe_ratio) FROM backtest_reports').fetchone()[0]
    print(f'Count: {cnt}, Avg Sharpe: {avg_sharpe:.2f}, Max Sharpe: {max_sharpe:.2f}')
except Exception as e:
    print(e)

# trades_log
print('\n--- trades_log ---')
try:
    cnt = c.execute('SELECT count(*) FROM trades_log').fetchone()[0]
    print(f'Count: {cnt}')
    rows = c.execute('SELECT * FROM trades_log ORDER BY ROWID DESC LIMIT 5').fetchall()
    for r in rows: print(r)
except Exception as e:
    print(e)