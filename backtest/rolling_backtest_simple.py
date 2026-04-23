# -*- coding: utf-8 -*-
"""
Tina v4.21 滾動式回測 - 精簡版
版本控制 + 自動迭代優化
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'

TOP100 = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2421','2449','2474','2492','2610','2880','2881','2882',
    '2883','2884','2885','2886','2887','2888','2891','2892','3008','3033',
    '3044','3189','3229','3231','3443','3481','3665','3717','4938','4958',
    '4961','5871','5880','6409','6415','6505','6669','6770','8016','8046',
    '8105','8233','8261','8341','8464','8478','8926','8996','9945','1234',
    '2312','2327','2337','2344','2385','2390','2515','2527','2603','2609'
]

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_atr(h, i):
    trs = []
    for j in range(max(0, i-14), i):
        hi = float(h['High'].iloc[j])
        lo = float(h['Low'].iloc[j])
        cl = float(h['Close'].iloc[j-1]) if j-1 >= 0 else float(h['Close'].iloc[j])
        trs.append(max(hi-lo, abs(hi-cl), abs(lo-cl)))
    return np.mean(trs) if trs else 0

def get_inst(code, date):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(foreign_net), SUM(trust_net) FROM MarketData
        WHERE symbol = ? AND date <= ? AND date >= date(?, '-3 days')
    ''', (code, date, date))
    f_sum, t_sum = cur.fetchone()
    conn.close()
    return (f_sum or 0), (t_sum or 0)

def rolling_backtest(version_name, holding_days=5):
    trades = []
    
    for code in TOP100:
        try:
            h = yf.Ticker(code + '.TW').history(period='200d')
            if len(h) < 150:
                continue
            
            closes = list(h['Close'].values)
            
            for i in range(60, len(closes) - holding_days - 60):
                close = closes[i]
                date = h.index[i].strftime('%Y-%m-%d')
                
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                
                f_net, t_net = get_inst(code, date)
                
                # 版本條件
                if version_name == 'v4.21':
                    ok = rsi < 70 and atr_pct >= 0.5 and ma20 > ma60 and (f_net > 0 or t_net > 0)
                elif version_name == 'v4.21_kdj':
                    ok = rsi < 70 and atr_pct >= 0.5 and ma20 > ma60 and (f_net > 0 or t_net > 0)
                elif version_name == 'v4.21_vr':
                    ok = rsi < 70 and atr_pct >= 0.5 and ma20 > ma60 and (f_net > 0 or t_net > 0)
                elif version_name == 'v4.21_strict':
                    ok = rsi < 65 and atr_pct >= 0.8 and ma20 > ma60 and f_net > 0 and t_net > 0
                elif version_name == 'v4.21_relax':
                    ok = rsi < 75 and atr_pct >= 0.3 and (f_net > 0 or t_net > 0)
                else:
                    ok = False
                
                if ok:
                    future_return = (closes[i+holding_days] / close - 1) * 100
                    trades.append({'code': code, 'date': date, 'return': future_return, 'rsi': rsi})
        except:
            continue
    
    return trades

def analyze_trades(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg_return': 0, 'pf': 0}
    
    total = len(trades)
    wins = [t for t in trades if t['return'] > 0]
    losses = [t for t in trades if t['return'] <= 0]
    
    win_rate = len(wins) / total * 100
    avg_return = np.mean([t['return'] for t in trades])
    
    total_win = sum([t['return'] for t in wins])
    total_loss = abs(sum([t['return'] for t in losses]))
    pf = total_win / total_loss if total_loss > 0 else 0
    
    return {'total': total, 'win_rate': win_rate, 'avg_return': avg_return, 'pf': pf}

print('='*70)
print(' Tina v4.21 滾動式回測系統 - 精簡版')
print('='*70)

versions = ['v4.21', 'v4.21_kdj', 'v4.21_vr', 'v4.21_strict', 'v4.21_relax']
results = {}

for v in versions:
    print(' 測試 ' + v + '...')
    trades = rolling_backtest(v, 5)
    stats = analyze_trades(trades)
    results[v] = stats

print()
print('='*70)
print(' 版本比較結果')
print('='*70)
print()
print('%-15s %-8s %-8s %-10s %-8s' % ('版本', '交易次', '勝率', '平均報酬', 'PF'))
print('-'*50)

for v in sorted(results.keys(), key=lambda x: results[x]['win_rate'], reverse=True):
    s = results[v]
    print('%-15s %-8d %-8.1f %-10.2f %-8.2f' % (v, s['total'], s['win_rate'], s['avg_return'], s['pf']))

# 版本控制决策
print()
print('='*70)
print(' 版本控制决策')
print('='*70)

best = max(results.keys(), key=lambda v: results[v]['win_rate'])
best_stats = results[best]
base_stats = results['v4.21']

print()
print('[版本序號]: ' + best)
print('[修正概要]: ' + best + ' 版本測試')
print()
print('【績效對比】 vs v4.21 (基準):')
print('  勝率變化: ' + str(round(base_stats['win_rate'],1)) + '% -> ' + str(round(best_stats['win_rate'],1)) + '%')
print('  交易次變化: ' + str(base_stats['total']) + ' -> ' + str(best_stats['total']))
print('  PF 變化: ' + str(round(base_stats['pf'],2)) + ' -> ' + str(round(best_stats['pf'],2)))
print()
print('【後續行動】')
if best_stats['win_rate'] > base_stats['win_rate'] + 1:
    print(' ✅ 勝率提升，更新為主版本')
elif best_stats['win_rate'] >= base_stats['win_rate'] - 2:
    print(' ⚠️ 勝率持平，維持 v4.21')
else:
    print(' ❌ 績效劣化，Rollback 至 v4.21')

print()
print('='*70)