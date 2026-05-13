import sqlite3
import json
from pathlib import Path
from datetime import datetime

conn = sqlite3.connect('unified_db/unified_trading.db')

print('='*70)
print('  Tina 交易策略優化分析報告')
print(f'  生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('='*70)

# 1. Overall performance
cur = conn.execute('SELECT COUNT(*), AVG(return_pct), MAX(return_pct), MIN(return_pct) FROM trades WHERE return_pct IS NOT NULL')
total, avg, best, worst = cur.fetchone()
cur2 = conn.execute('SELECT COUNT(*) FROM trades WHERE return_pct > 0')
wins = cur2.fetchone()[0]
cur3 = conn.execute('SELECT COUNT(*) FROM trades WHERE return_pct < 0')
losses = cur3.fetchone()[0]

print()
print('【1. 整體績效】')
print(f'  總交易筆數: {total}')
print(f'  勝率: {wins/total*100:.1f}% ({wins}勝/{losses}敗)')
print(f'  平均報酬: {avg:+.3f}%')
print(f'  最佳交易: +{best:.2f}%')
print(f'  最差交易: {worst:.2f}%')

# 2. Best stocks by win rate
print()
print('【2. 最佳標的 (勝率 100%, 至少3筆交易)】')
print('-'*70)
cur = conn.execute('''
    SELECT symbol, COUNT(*) as trades, AVG(return_pct) as avg_ret
    FROM trades 
    WHERE return_pct IS NOT NULL
    GROUP BY symbol
    HAVING COUNT(*) >= 3 AND AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) = 1
    ORDER BY avg_ret DESC
''')
for row in cur.fetchall():
    sym, trades, ret = row
    print(f'  {sym:<10} {trades:>3} trades  Avg: {ret:+.2f}%')

# 3. Top performers by sector
print()
print('【3. 產業板塊表現】')
print('-'*70)
cur = conn.execute('''
    SELECT sector, COUNT(*) as trades,
           AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
           AVG(return_pct) as avg_ret
    FROM trades
    WHERE sector IS NOT NULL AND return_pct IS NOT NULL
    GROUP BY sector
    ORDER BY win_rate DESC, avg_ret DESC
''')
for row in cur.fetchall():
    sector, trades, wr, ret = row
    wr_str = f'{wr:.1f}%'
    ret_str = f'{ret:+.2f}%'
    print(f'  {sector:<20} {trades:>4} trades  WR: {wr_str:>7}  Avg: {ret_str:>8}')

# 4. Hold days analysis
print()
print('【4. 持有天數分析】')
print('-'*70)
cur = conn.execute('''
    SELECT 
        CASE 
            WHEN hold_days <= 5 THEN '1-5天'
            WHEN hold_days <= 10 THEN '6-10天'
            WHEN hold_days <= 15 THEN '11-15天'
            WHEN hold_days <= 20 THEN '16-20天'
            ELSE '20天+'
        END as hold_range,
        COUNT(*) as trades,
        AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
        AVG(return_pct) as avg_ret
    FROM trades
    WHERE hold_days IS NOT NULL AND return_pct IS NOT NULL
    GROUP BY hold_range
    ORDER BY avg_ret DESC
''')
for row in cur.fetchall():
    hr, trades, wr, ret = row
    print(f'  {hr:<10} {trades:>5} trades  WR: {wr:>5.1f}%  Avg: {ret:>+6.2f}%')

# 5. RSI entry analysis
print()
print('【5. RSI 進場區間分析】')
print('-'*70)
cur = conn.execute('''
    SELECT 
        CASE 
            WHEN rsi_entry < 30 THEN 'RSI < 30'
            WHEN rsi_entry < 40 THEN 'RSI 30-40'
            WHEN rsi_entry < 50 THEN 'RSI 40-50'
            WHEN rsi_entry < 60 THEN 'RSI 50-60'
            WHEN rsi_entry < 70 THEN 'RSI 60-70'
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
for row in cur.fetchall():
    rr, trades, wr, ret = row
    print(f'  {rr:<12} {trades:>5} trades  WR: {wr:>5.1f}%  Avg: {ret:>+6.2f}%')

# 6. System comparison
print()
print('【6. 系統表現比較】')
print('-'*70)
cur = conn.execute('''
    SELECT system, COUNT(*) as trades,
           AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
           AVG(return_pct) as avg_ret
    FROM trades
    WHERE system IS NOT NULL AND return_pct IS NOT NULL
    GROUP BY system
    ORDER BY win_rate DESC, avg_ret DESC
''')
for row in cur.fetchall():
    sys, trades, wr, ret = row
    print(f'  {sys:<15} {trades:>5} trades  WR: {wr:>5.1f}%  Avg: {ret:>+6.2f}%')

# 7. Market comparison
print()
print('【7. 市場比較 (台股 vs 美股)】')
print('-'*70)
cur = conn.execute('''
    SELECT market, COUNT(*) as trades,
           AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
           AVG(return_pct) as avg_ret
    FROM trades
    WHERE market IS NOT NULL AND return_pct IS NOT NULL
    GROUP BY market
    ORDER BY win_rate DESC, avg_ret DESC
''')
for row in cur.fetchall():
    mkt, trades, wr, ret = row
    print(f'  {mkt:<10} {trades:>5} trades  WR: {wr:>5.1f}%  Avg: {ret:>+6.2f}%')

# 8. Optimal parameters
print()
print('【8. 最佳化參數建議】')
print('-'*70)

# Find best RSI + hold_days combination
cur = conn.execute('''
    SELECT 
        CASE 
            WHEN rsi_entry < 30 THEN 'RSI < 30'
            WHEN rsi_entry < 40 THEN 'RSI 30-40'
            WHEN rsi_entry < 50 THEN 'RSI 40-50'
            ELSE 'RSI 50+'
        END as rsi_range,
        CASE 
            WHEN hold_days <= 5 THEN '1-5天'
            WHEN hold_days <= 10 THEN '6-10天'
            WHEN hold_days <= 15 THEN '11-15天'
            ELSE '16天+'
        END as hold_range,
        COUNT(*) as trades,
        AVG(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
        AVG(return_pct) as avg_ret
    FROM trades
    WHERE rsi_entry IS NOT NULL AND hold_days IS NOT NULL AND return_pct IS NOT NULL
    GROUP BY rsi_range, hold_range
    HAVING COUNT(*) >= 10
    ORDER BY win_rate DESC, avg_ret DESC
    LIMIT 10
''')

print('  RSI 區間 + 持有天數 組合 (至少10筆交易):')
print('  ' + '-'*60)
for row in cur.fetchall():
    rr, hr, trades, wr, ret = row
    print(f'  {rr:<12} + {hr:<8} → WR: {wr:>5.1f}%  Avg: {ret:>+6.2f}%  ({trades}筆)')

# 9. Active holdings vs closed performance
print()
print('【9. 倉位狀態分析】')
print('-'*70)
cur = conn.execute('''
    SELECT status, COUNT(*) as count, AVG(return_pct) as avg_ret
    FROM trades
    WHERE status IS NOT NULL AND return_pct IS NOT NULL
    GROUP BY status
''')
for row in cur.fetchall():
    status, cnt, ret = row
    print(f'  {status:<15} {cnt:>4} 筆  Avg: {ret:+.2f}%')

conn.close()

print()
print('='*70)
print('  建議: 以 RSI 40-50 + 持有 6-10 天 為主要策略')
print('  產業: 優先選擇 半導體/IC設計 類股')
print('  市場: 美股波段操作空間較大')
print('='*70)