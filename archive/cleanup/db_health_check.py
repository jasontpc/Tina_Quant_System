import sqlite3
conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()

print('=== 資料庫健檢 ===')
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [t[0] for t in c.fetchall()]
print('Tables:', tables)

for t in tables:
    c.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'  {t}: {c.fetchone()[0]} rows')

print()
print('=== backtest_reports 交易策略 TOP 20 ===')
c.execute('''SELECT strategy_name, indicator, sharpe_ratio, max_drawdown, win_rate, num_trades, symbol 
             FROM backtest_reports ORDER BY sharpe_ratio DESC LIMIT 20''')
headers = ['Strategy', 'Indicator', 'Sharpe', 'MDD', 'Win%', 'Trades', 'Symbol']
print('  ' + ' | '.join(f'{h:15}' for h in headers))
print('  ' + '-'*120)
for row in c.fetchall():
    print('  ' + ' | '.join(f'{str(v)[:15]:15}' for v in row))

print()
print('=== wisdom_corrections 修正記錄 ===')
c.execute('SELECT axiom_id, symbol, confidence, model_used FROM wisdom_corrections ORDER BY id DESC LIMIT 10')
for row in c.fetchall():
    print(f'  axiom={row[0]} | symbol={row[1]} | conf={row[2]} | model={row[3]}')

print()
print('=== wisdom_logs weight 分佈 ===')
c.execute('''SELECT 
    SUM(CASE WHEN weight > 2.0 THEN 1 ELSE 0 END) as high,
    SUM(CASE WHEN weight BETWEEN 1.0 AND 2.0 THEN 1 ELSE 0 END) as normal,
    SUM(CASE WHEN weight < 1.0 THEN 1 ELSE 0 END) as low,
    SUM(CASE WHEN weight IS NULL THEN 1 ELSE 0 END) as null_w
    FROM wisdom_logs''')
row = c.fetchone()
print(f'  weight > 2.0 (高): {row[0]}')
print(f'  weight 1.0-2.0 (正常): {row[1]}')
print(f'  weight < 1.0 (衰減): {row[2]}')
print(f'  weight NULL: {row[3]}')

conn.close()