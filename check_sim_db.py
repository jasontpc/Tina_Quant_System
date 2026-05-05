import sqlite3, os
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy_sim_trades.db'
size = os.path.getsize(db) / 1024
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM sim_trades')
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM trade_summary')
summary = cur.fetchone()[0]

print(f'DB: maggy_sim_trades.db')
print(f'Size: {size:.0f} KB')
print(f'Total trades: {total}')
print(f'Stock summaries: {summary}')

cur.execute('SELECT symbol, total_trades, win_rate, total_return FROM trade_summary ORDER BY total_return DESC LIMIT 10')
print()
print('Top 10 stocks:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]} trades WR={r[2]:.1f}% return={r[3]:+.1f}%')

# Best trades
cur.execute('SELECT symbol, entry_date, exit_date, return_pct, holding_days FROM sim_trades ORDER BY return_pct DESC LIMIT 5')
print()
print('Best 5 trades:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1][:10]}~{r[2][:10]} {r[3]:+.2f}% {r[4]}days')

conn.close()