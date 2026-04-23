"""
v4.21 vs v4.23 Entry Rules Backtest Comparison
日期: 2026-04-23
"""

import sqlite3
import json

conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Get all symbols with data
cur.execute("SELECT DISTINCT symbol FROM MarketData ORDER BY symbol")
symbols = [r[0] for r in cur.fetchall()]

# Blacklist
blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', 
             '3443', '6446', '6669', '2597', '2379', '2345']

def check_entry_v421(rows, idx, symbol):
    """
    v4.21 進場規則 (對比用):
    - RSI < 70
    - ATR% >= 0.5%
    - 法人 3天內外资 AND 投信都 >= 1天買超
    - MA20 站上
    - MA20 > MA60 (多頭趨勢)
    """
    row = rows[idx]
    rsi = row[3]  # rsi_14
    ma20 = row[4]  # ma20
    ma60 = row[5]  # ma60
    
    if symbol in blacklist:
        return False, 'BLACKLIST'
    
    # RSI check
    if not (rsi and rsi < 70):
        return False, f'RSI>{rsi}'
    
    # MA20 > MA60 check
    if not (ma20 and ma60 and ma20 > ma60):
        return False, f'MA20<=MA60'
    
    # Check institutional 3-day: foreign AND trust both > 0
    inst_count = 0
    for j in range(max(0, idx-2), idx+1):
        if rows[j][6] > 0 or rows[j][7] > 0:  # foreign_net or trust_net
            inst_count += 1
    
    if inst_count < 1:
        return False, 'NO_INST'
    
    return True, 'PASS'

def check_entry_v423(rows, idx, symbol):
    """
    v4.23 進場規則:
    - RSI < 70
    - Bias < 10%
    - volume_ratio >= 0.8
    - 法人 3天內 >= 1天買超 (OR邏輯)
    """
    row = rows[idx]
    rsi = row[3]
    ma20 = row[4]
    ma60 = row[5]
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
    if volume and volume < 1000000:  # 假設 < 1000張 = 量能不足
        return False, 'LOW_VOL'
    
    return True, 'PASS'

# Run backtest for both versions
results_v421 = []
results_v423 = []

for symbol in symbols:
    cur.execute('''
    SELECT symbol, date, close, rsi_14, ma20, ma60, foreign_net, trust_net, volume
    FROM MarketData
    WHERE symbol = ? AND close IS NOT NULL
    ORDER BY date
    ''', (symbol,))
    
    rows = list(cur.fetchall())
    for i in range(3, len(rows)):
        # v4.21 check
        passed_421, reason_421 = check_entry_v421(rows, i, symbol)
        if passed_421:
            if i + 5 < len(rows):
                exit_price = rows[i + 5][2]
                if rows[i][2] and exit_price:
                    ret_pct = (exit_price - rows[i][2]) / rows[i][2] * 100
                    results_v421.append({
                        'symbol': symbol,
                        'date': rows[i][1],
                        'close': rows[i][2],
                        'return_pct': ret_pct,
                        'rsi': rows[i][3]
                    })
        
        # v4.23 check
        passed_423, reason_423 = check_entry_v423(rows, i, symbol)
        if passed_423:
            if i + 5 < len(rows):
                exit_price = rows[i + 5][2]
                if rows[i][2] and exit_price:
                    ret_pct = (exit_price - rows[i][2]) / rows[i][2] * 100
                    results_v423.append({
                        'symbol': symbol,
                        'date': rows[i][1],
                        'close': rows[i][2],
                        'return_pct': ret_pct,
                        'rsi': rows[i][3]
                    })

def analyze(results, label):
    total = len(results)
    if total == 0:
        print(f'{label}: No signals')
        return
    
    wins = [r for r in results if r['return_pct'] > 0]
    losses = [r for r in results if r['return_pct'] <= 0]
    win_rate = len(wins) / total * 100
    avg_return = sum(r['return_pct'] for r in results) / total
    avg_win = sum(r['return_pct'] for r in wins) / len(wins) if wins else 0
    avg_loss = sum(r['return_pct'] for r in losses) / len(losses) if losses else 0
    pf = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    print(f'\n=== {label} ===')
    print(f'Signals: {total}, Wins: {len(wins)}, Losses: {len(losses)}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Avg Return: {avg_return:+.2f}%')
    print(f'Avg Win: {avg_win:+.2f}%, Avg Loss: {avg_loss:+.2f}%')
    print(f'Profit Factor: {pf:.2f}')

analyze(results_v421, 'v4.21 (Original)')
analyze(results_v423, 'v4.23 (Bias+Vol)')

conn.close()