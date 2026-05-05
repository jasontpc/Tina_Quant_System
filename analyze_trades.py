import sqlite3
conn = sqlite3.connect('unified_db/unified_trading.db')

# Best performing stocks
cur = conn.execute('''
    SELECT symbol, COUNT(*) as trades, 
           AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
           AVG(return_pct) as avg_ret,
           MAX(return_pct) as best,
           MIN(return_pct) as worst
    FROM trades 
    WHERE return_pct IS NOT NULL
    GROUP BY symbol
    HAVING COUNT(*) >= 3
    ORDER BY win_rate DESC, avg_ret DESC
    LIMIT 10
''')

print('='*60)
print('  Top 10 by Win Rate (min 3 trades)')
print('='*60)
print('Symbol       Trades  WinRate   AvgRet    Best    Worst')
print('-'*60)
for row in cur.fetchall():
    sym, trades, wr, ret, best, worst = row
    print(f'{sym:<10} {trades:>6} {wr:>7.1f}% {ret:>+7.2f}% {best:>+7.2f}% {worst:>+7.2f}%')

# Overall stats
cur2 = conn.execute('SELECT COUNT(*), AVG(return_pct), MAX(return_pct), MIN(return_pct) FROM trades WHERE return_pct IS NOT NULL')
total, avg, best_all, worst_all = cur2.fetchone()
cur3 = conn.execute('SELECT COUNT(*) FROM trades WHERE return_pct > 0')
wins = cur3.fetchone()[0]

print()
print('='*60)
print(f'Overall: {total} trades, Win Rate: {wins/total*100:.1f}%, Avg: {avg:+.2f}%')
print(f'Best trade: +{best_all:.2f}%, Worst: {worst_all:.2f}%')

# Best RSI entry range
print()
print('Best RSI Entry Ranges:')
print('-'*60)
cur4 = conn.execute('''
    SELECT 
        CASE 
            WHEN rsi_entry < 30 THEN 'RSI < 30'
            WHEN rsi_entry >= 30 AND rsi_entry < 40 THEN 'RSI 30-40'
            WHEN rsi_entry >= 40 AND rsi_entry < 50 THEN 'RSI 40-50'
            WHEN rsi_entry >= 50 AND rsi_entry < 60 THEN 'RSI 50-60'
            WHEN rsi_entry >= 60 AND rsi_entry < 70 THEN 'RSI 60-70'
            ELSE 'RSI >= 70'
        END as rsi_range,
        COUNT(*) as trades,
        AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
        AVG(return_pct) as avg_ret
    FROM trades
    WHERE rsi_entry IS NOT NULL AND return_pct IS NOT NULL
    GROUP BY rsi_range
    ORDER BY win_rate DESC, avg_ret DESC
''')

for row in cur4:
    rsi_range, trades, wr, ret = row
    print(f'{rsi_range:<15} {trades:>5} trades  WR:{wr:>5.1f}%  Avg:{ret:>+6.2f}%')

conn.close()
print('='*60)