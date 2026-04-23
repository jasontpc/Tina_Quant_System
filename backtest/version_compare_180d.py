# -*- coding: utf-8 -*-
"""
Tina 版本比較回測 - 180天完整回測
v4.21 vs v4.3 vs v4.22
市值前100大
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
from datetime import datetime, timedelta

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# Top 100 (精簡)
TOP100 = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2421','2449','2474','2492','2610','2880','2881','2882',
    '2883','2884','2885','2886','2887','2888','2891','2892','3008','3033',
    '3044','3189','3229','3231','3443','3481','3665','3717','4938','4958',
    '4961','5871','5880','6409','6415','6505','6669','6770','8016','8046',
    '8105','8233','8261','8341','8464','8478','8926','8996','9945','1234',
    '2312','2327','2337','2344','2385','2390','2515','2527','2603','2609',
    '2707','2823','2834','2855','2912','2939','3029','3045','3088','3105',
    '3234','3257','3294','3305','3380','3416','3443','3533','3557','3593',
    '3596','3610','3673','3686','3702','3711','3722','4001','4002','4904'
]

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_atr(h, pos=-1):
    trs = []
    for i in range(pos-14, pos):
        if i < 0:
            continue
        hi = float(h['High'].iloc[i])
        lo = float(h['Low'].iloc[i])
        cl = float(h['Close'].iloc[i-1]) if i-1 >= 0 else float(h['Close'].iloc[i])
        trs.append(max(hi-lo, abs(hi-cl), abs(lo-cl)))
    return np.mean(trs) if trs else 0

def check_inst(code, date):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM MarketData
        WHERE symbol = ? AND date <= ? AND date >= date(?, '-3 days')
        AND (foreign_net > 0 OR trust_net > 0)
    ''', (code, date, date))
    count = cur.fetchone()[0]
    conn.close()
    return count >= 1

def backtest_version(version, holding_days=5):
    trades = []
    
    for code in TOP100:
        try:
            h = yf.Ticker(code + '.TW').history(period='200d')
            if len(h) < 180:
                continue
            
            closes = list(h['Close'].values)
            
            # 180天回測 (每天檢查信號)
            for i in range(90, len(closes) - holding_days):
                close = closes[i]
                prev_close = closes[i-1]
                change = (close / prev_close - 1) * 100
                
                # 取得技術指標 (過去20日)
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                
                # 取得日期
                date = h.index[i].strftime('%Y-%m-%d')
                inst = check_inst(code, date)
                
                # 各版本條件
                if version == 'v4.21':
                    ok = rsi < 70 and atr_pct >= 0.5 and ma20 > ma60 and inst
                elif version == 'v4.3':
                    ok = 40 <= rsi <= 70 and atr_pct >= 0.3 and inst
                elif version == 'v4.22':
                    # v4.22: RSI<75, MA20>MA60, Inst
                    ok = rsi < 75 and ma20 > ma60 and inst
                else:
                    ok = False
                
                if ok:
                    # 計算持有N日後的報酬
                    future_return = (closes[i+holding_days] / close - 1) * 100
                    trades.append({
                        'code': code,
                        'date': date,
                        'entry': close,
                        'exit': closes[i+holding_days],
                        'return': future_return,
                        'rsi': rsi,
                        'atr': atr_pct
                    })
        except:
            continue
    
    return trades

print('='*65)
print(' Tina 版本比較 - 180天完整回測')
print(' 持有天數: 5天')
print('='*65)

results = {}
for v in ['v4.21', 'v4.3', 'v4.22']:
    print()
    print(' 正在回測 ' + v + '...')
    trades = backtest_version(v, 5)
    results[v] = trades

print()
print('='*65)
print(' 回測結果比較')
print('='*65)

summary = []
for v, trades in results.items():
    total = len(trades)
    if total == 0:
        print()
        print(' ' + v + ': 無資料')
        continue
    
    wins = [t for t in trades if t['return'] > 0]
    losses = [t for t in trades if t['return'] <= 0]
    
    win_rate = len(wins) / total * 100
    avg_return = np.mean([t['return'] for t in trades])
    avg_win = np.mean([t['return'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['return'] for t in losses]) if losses else 0
    
    # 計算 PF
    total_win = sum([t['return'] for t in wins])
    total_loss = abs(sum([t['return'] for t in losses]))
    pf = total_win / total_loss if total_loss > 0 else 0
    
    summary.append({
        'version': v,
        'total': total,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'pf': pf
    })
    
    print()
    print('【' + v + '】')
    print(' 總交易次數: ' + str(total))
    print(' 勝率: ' + str(round(win_rate,1)) + '%')
    print(' 平均報酬: ' + str(round(avg_return,2)) + '%')
    print(' 平均獲利: ' + str(round(avg_win,2)) + '%')
    print(' 平均虧損: ' + str(round(avg_loss,2)) + '%')
    print(' 獲利因子: ' + str(round(pf,2)))
    
    if total >= 5:
        print()
        print(' 前5筆交易:')
        sorted_trades = sorted(trades, key=lambda x: x['return'], reverse=True)
        for j, t in enumerate(sorted_trades[:5], 1):
            icon = '▲' if t['return'] > 0 else '▼'
            print('  ' + str(j) + '. ' + t['code'] + ' ' + t['date'] + ' ' + icon + str(round(abs(t['return']),1)) + '%')

print()
print('='*65)
print(' 總結比較')
print('='*65)
print()
print('%-8s %-8s %-8s %-10s %-8s %-8s' % ('版本', '交易次', '勝率', '平均報酬', '平均獲利', 'PF'))
print('-'*65)

for s in summary:
    print('%-8s %-8d %-8.1f %-10.2f %-8.2f %-8.2f' % (
        s['version'], s['total'], s['win_rate'], s['avg_return'], s['avg_win'], s['pf']))

print()
print('='*65)