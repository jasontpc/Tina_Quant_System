# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'
STOCKS = [('2891', '中信金'), ('2385', '精英'), ('2353', '兆赫')]

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('='*70)
print(' 法人資金流向 (近10天)')
print('='*70)

for code, name in STOCKS:
    cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', (code,))
    rows = cur.fetchall()
    
    print('\n【%s %s】' % (code, name))
    print('-'*50)
    print('日期        外資買賣       投信買賣')
    print('-'*50)
    
    for date, f, t in rows:
        f_str = '%+10.0f' % f if f else '         -'
        t_str = '%+10.0f' % t if t else '         -'
        f_a = '↑' if f and f > 0 else '↓' if f and f < 0 else ' '
        t_a = '↑' if t and t > 0 else '↓' if t and t < 0 else ' '
        print('%s  %s %s  %s %s' % (date, f_str, f_a, t_str, t_a))

conn.close()
print()
print('='*70)
print(' ↑ = 買超 | ↓ = 賣超 | - = 無資料')
print('='*70)