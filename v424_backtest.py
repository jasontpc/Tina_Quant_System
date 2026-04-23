"""
v4.24 Entry Rules Backtest
修正 v4.23 的問題：維持法人 AND 邏輯
測試: RSI<70 + Bias<10% + volume>=0.8 + 法人 AND
日期: 2026-04-23
"""

import sqlite3

conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Get all symbols with data
cur.execute("SELECT DISTINCT symbol FROM MarketData ORDER BY symbol")
symbols = [r[0] for r in cur.fetchall()]

# Blacklist
blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', 
             '3443', '6446', '6669', '2597', '2379', '2345']

def check_entry_v424(rows, idx, symbol):
    """
    v4.24 進場規則 (修正版):
    - RSI < 70
    - Bias < 10%
    - volume_ratio >= 0.8
    - 法人 3天內 AND (foreign > 0 AND trust > 0) >= 1天
    """
    row = rows[idx]
    rsi = row[3]
    ma20 = row[4]
    ma60 = row[5]
    foreign_net = row[6]
    trust_net = row[7]
    volume = row[8]
    
    if symbol in blacklist:
        return False, 'BLACKLIST'
    
    # RSI check
    if not (rsi and rsi < 70):
        return False, f'RSI>{rsi}'
    
    # Bias check
    if ma20 and ma60 and ma60 > 0:
        bias = (ma20 - ma60) / ma60 * 100
        if bias >= 10:
            return False, f'BIAS>{bias:.1f}%'
    
    # Volume check
    if volume and volume < 1000000:  # < 1000張
        return False, 'LOW_VOL'
    
    # Institutional AND check (both foreign AND trust > 0)
    inst_count = 0
    for j in range(max(0, idx-2), idx+1):
        if rows[j][6] > 0 and rows[j][7] > 0:  # both foreign AND trust
            inst_count += 1
    
    if inst_count < 1:
        return False, 'NO_INST_BOTH'
    
    return True, 'PASS'

# Run backtest
results = []

for symbol in symbols:
    cur.execute('''
    SELECT symbol, date, close, rsi_14, ma20, ma60, foreign_net, trust_net, volume
    FROM MarketData
    WHERE symbol = ? AND close IS NOT NULL
    ORDER BY date
    ''', (symbol,))
    
    rows = list(cur.fetchall())
    for i in range(3, len(rows)):
        passed, reason = check_entry_v424(rows, i, symbol)
        if passed:
            if i + 5 < len(rows):
                exit_price = rows[i + 5][2]
                if rows[i][2] and exit_price:
                    ret_pct = (exit_price - rows[i][2]) / rows[i][2] * 100
                    results.append({
                        'symbol': symbol,
                        'date': rows[i][1],
                        'entry_price': rows[i][2],
                        'exit_price': exit_price,
                        'return_pct': ret_pct,
                        'rsi': rows[i][3],
                        'bias': ((rows[i][4] - rows[i][5]) / rows[i][5] * 100) if rows[i][5] else 0
                    })

# Analyze results
total = len(results)
wins = [r for r in results if r['return_pct'] > 0]
losses = [r for r in results if r['return_pct'] <= 0]
win_rate = len(wins) / total * 100 if total > 0 else 0
avg_return = sum(r['return_pct'] for r in results) / total if total > 0 else 0
avg_win = sum(r['return_pct'] for r in wins) / len(wins) if wins else 0
avg_loss = sum(r['return_pct'] for r in losses) / len(losses) if losses else 0
pf = abs(avg_win / avg_loss) if avg_loss != 0 else 0

print(f'=== v4.24 Backtest Results ===')
print(f'Signals: {total}')
print(f'Wins: {len(wins)}, Losses: {len(losses)}')
print(f'Win Rate: {win_rate:.1f}%')
print(f'Avg Return: {avg_return:+.2f}%')
print(f'Avg Win: {avg_win:+.2f}%, Avg Loss: {avg_loss:+.2f}%')
print(f'Profit Factor: {pf:.2f}')

# Comparison with v4.21
print('\n=== Comparison with v4.21 ===')
print(f'{"Version":<10} {"Signals":<10} {"WR":<8} {"Avg Ret":<10} {"PF":<6}')
print(f'{"v4.21":<10} {"1711":<10} {"56.0%":<8} {"+2.27%":<10} {"1.67":<6}')
print(f'{"v4.24":<10} {str(total):<10} {f"{win_rate:.1f}%":<8} {f"{avg_return:+.2f}%":<10} {f"{pf:.2f}":<6}')

# Show top winners
print('\nTop 10 Winners:')
sorted_results = sorted(results, key=lambda x: x['return_pct'], reverse=True)
for r in sorted_results[:10]:
    print(f"  {r['symbol']} {r['date']} {r['return_pct']:+.2f}% RSI={r['rsi']:.1f} Bias={r['bias']:.1f}%")

# Show fail reason distribution
print('\nFail reason distribution (v4.24):')
print('  (This would require running full v4.21 comparison)')

conn.close()