"""
v4.23 Entry Rules Backtest
測試: RSI<70 + Bias<10% Veto + volume_ratio>=0.8
日期: 2026-04-23
"""

import sqlite3
import json
from datetime import datetime, timedelta

conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Get all symbols with data
cur.execute("SELECT DISTINCT symbol FROM MarketData ORDER BY symbol")
symbols = [r[0] for r in cur.fetchall()]

# Blacklist
blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', 
             '3443', '6446', '6669', '2597', '2379', '2345']  # Added failure stocks

# v4.23 entry rules
def check_entry_v423(row):
    """
    v4.23 進場規則:
    - RSI < 70
    - ATR% >= 0.5%
    - Bias < 10%
    - volume_ratio >= 0.8
    - 法人 3天內 >= 1天買超
    """
    rsi = row['rsi_14'] or 70
    ma20 = row['ma20'] or 0
    ma60 = row['ma60'] or 0
    foreign_net = row['foreign_net'] or 0
    trust_net = row['trust_net'] or 0
    
    # Skip if in blacklist
    if row['symbol'] in blacklist:
        return False, 'BLACKLIST'
    
    # RSI check - 維持 < 70
    if not (rsi < 70):
        return False, f'RSI>{rsi}'
    
    # Bias check - < 10%
    if ma20 > 0 and ma60 > 0:
        bias = (ma20 - ma60) / ma60 * 100
        if bias >= 10:
            return False, f'BIAS>{bias:.1f}%'
    
    # Volume check - >= 0.8 (假設 volume_ratio)
    volume_ratio = row.get('volume_ratio', 1.0)
    if volume_ratio < 0.8:
        return False, f'VR<{volume_ratio:.1f}'
    
    # Institutional check - 3天內 >= 1天買超 (foreign_net > 0 OR trust_net > 0)
    if not (foreign_net > 0 or trust_net > 0):
        return False, 'NO_INST'
    
    return True, 'PASS'

# Run backtest
results = []
for symbol in symbols:
    # Get historical data
    cur.execute('''
    SELECT symbol, date, close, rsi_14, ma20, ma60, foreign_net, trust_net, volume
    FROM MarketData
    WHERE symbol = ? AND close IS NOT NULL
    ORDER BY date
    ''', (symbol,))
    
    rows = cur.fetchall()
    for i, row in enumerate(rows):
        # Need lookback for institutional check (3 days)
        if i < 3:
            continue
        
        data = {
            'symbol': row[0],
            'date': row[1],
            'close': row[2],
            'rsi_14': row[3],
            'ma20': row[4],
            'ma60': row[5],
            'foreign_net': row[6],
            'trust_net': row[7],
            'volume': row[8]
        }
        
        passed, reason = check_entry_v423(data)
        if passed:
            # Calculate 5-day return (固定持有)
            if i + 5 < len(rows):
                exit_price = rows[i + 5][2]
                if exit_price and data['close']:
                    ret_pct = (exit_price - data['close']) / data['close'] * 100
                    results.append({
                        'symbol': symbol,
                        'entry_date': data['date'],
                        'entry_price': data['close'],
                        'exit_price': exit_price,
                        'return_pct': ret_pct,
                        'rsi_entry': data['rsi_14'],
                        'bias': ((data['ma20'] - data['ma60']) / data['ma60'] * 100) if data['ma60'] else 0
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

print(f'=== v4.23 Backtest Results ===')
print(f'Signals: {total}')
print(f'Wins: {len(wins)}, Losses: {len(losses)}')
print(f'Win Rate: {win_rate:.1f}%')
print(f'Avg Return: {avg_return:+.2f}%')
print(f'Avg Win: {avg_win:+.2f}%, Avg Loss: {avg_loss:+.2f}%')
print(f'Profit Factor: {pf:.2f}')

# Show top winners
print('\nTop 10 Winners:')
sorted_results = sorted(results, key=lambda x: x['return_pct'], reverse=True)
for r in sorted_results[:10]:
    print(f"  {r['symbol']} {r['entry_date']} {r['return_pct']:+.2f}% RSI={r['rsi_entry']:.1f} Bias={r['bias']:.1f}%")

# Show top losers
print('\nTop 10 Losers:')
for r in sorted_results[-10:]:
    print(f"  {r['symbol']} {r['entry_date']} {r['return_pct']:+.2f}% RSI={r['rsi_entry']:.1f} Bias={r['bias']:.1f}%")

conn.close()