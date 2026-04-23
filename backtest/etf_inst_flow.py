# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'

ETFS = [
    ('0050', '元大台灣50'),
    ('00662', '富邦NASDAQ100'),
    ('00830', '富邦NASDAQ'),
    ('00757', '統一FANG+'),
    ('0056', '元大高股息'),
    ('00713', '元大台灣高息低波'),
    ('00927', '永豐優息存股'),
]

print('='*75)
print(' ETF 法人資金流向 (近10天)')
print('='*75)

conn = sqlite3.connect(DB)
cur = conn.cursor()

for code, name in ETFS:
    print()
    print(f'【{code} {name}】')
    print('  日期      外資            投信           評估')
    print('  ' + '-'*60)
    
    cur.execute('''
        SELECT date, foreign_net, trust_net 
        FROM MarketData 
        WHERE symbol = ? 
        ORDER BY date DESC 
        LIMIT 10
    ''', (code,))
    
    rows = cur.fetchall()
    
    if not rows:
        print('  無資料')
        continue
    
    f_3d = t_3d = 0
    count = 0
    
    for date, f, t in rows:
        if count < 3:
            f_3d += f if f else 0
            t_3d += t if t else 0
        count += 1
        
        f_str = '%+10.0f' % f if f else '         -'
        t_str = '%+10.0f' % t if t else '         -'
        f_a = '↑' if f and f > 0 else '↓' if f and f < 0 else ' '
        t_a = '↑' if t and t > 0 else '↓' if t and t < 0 else ' '
        
        # 評估
        if f and f > 0 and t and t > 0:
            ev = '雙多'
        elif f and f > 0:
            ev = '外资偏多'
        elif t and t > 0:
            ev = '投信偏多'
        elif f and f < 0 and t and t < 0:
            ev = '雙空'
        else:
            ev = '-'
        
        print(f'  {date}  {f_str} {f_a}  {t_str} {t_a}  {ev}')
    
    # 近3日合計
    f_3d_avg = f_3d / 3 if count >= 3 else f_3d / count if count > 0 else 0
    t_3d_avg = t_3d / 3 if count >= 3 else t_3d / count if count > 0 else 0
    
    print()
    print(f'  近3日合計: 外資 {f_3d:+,.0f} | 投信 {t_3d:+,.0f}')
    
    if f_3d > 0 and t_3d > 0:
        print(f'  方向: 🟢 雙多')
    elif f_3d > 0:
        print(f'  方向: 🟢 外资偏多')
    elif t_3d > 0:
        print(f'  方向: 🟡 投信偏多')
    else:
        print(f'  方向: 🔴 偏空')

conn.close()
print()
print('='*75)
print(' 📊 法人指標說明: ↑=買超  ↓=賣超')
print('='*75)