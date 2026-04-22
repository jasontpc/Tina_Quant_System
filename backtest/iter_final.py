# -*- coding: utf-8 -*-
"""
Q1 2026 - 技術+法人 迭代優化
目標: 提升勝率及交易次數
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf
yf.suppress_errors=True
import numpy as np
import sqlite3
import pandas as pd
import time

DB = 'skills/stock-analyzer/scripts/tina_master.db'

def load_inst():
    inst = {}
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
    for sym, date, f, t in cur.fetchall():
        if sym not in inst: inst[sym] = {}
        inst[sym][date] = (f or 0, t or 0)
    conn.close()
    return inst

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr(h, i):
    high = list(h['High'].iloc[max(0,i-14):i+1])
    low = list(h['Low'].iloc[max(0,i-14):i+1])
    close = list(h['Close'].iloc[max(0,i-14):i+1])
    tr = [max(high[j]-low[j], abs(high[j]-close[j-1]), abs(low[j]-close[j-1])) for j in range(1, len(high))]
    return np.mean(tr[-14:]) if len(tr) >= 14 else 30

def bt(params, stocks, inst_map):
    all_trades = []
    for code in stocks:
        try:
            h = yf.Ticker(code+'.TW').history(start='2026-01-01', end='2026-03-31')
            if len(h) < 25: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-20:i])
                atr = calc_atr(h, i)
                vr = vol[i] / np.mean(vol[i-20:i]) if np.mean(vol[i-20:i]) > 0 else 0
                date_str = str(h.index[i])[:10]
                
                if rs >= params.get('max_rsi', 65): continue
                if cl[i] < ma20: continue
                if atr < params.get('min_atr', 30): continue
                
                # VIF check
                if params.get('min_vif', 0) > 0 and vr < params['min_vif']: continue
                
                # Institutional filter
                inst_days = params.get('inst_days', 3)
                if inst_days > 0 and code in inst_map:
                    f_days, t_days = 0, 0
                    for d in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < params.get('inst_min', 1): continue
                elif inst_days > 0:
                    continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6,len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'rsi': rs, 'vr': vr, 'atr': atr, 'code': code})
        except:
            pass
        time.sleep(0.05)
    return all_trades

def analyze_failures(trades):
    losses = [t for t in trades if t['ret'] <= 0]
    if not losses: return {}
    return {
        'total': len(losses),
        'high_rsi': len([t for t in losses if t['rsi'] >= 60]),
        'low_vif': len([t for t in losses if t.get('vr', 0) < 1.5]),
        'low_atr': len([t for t in losses if t.get('atr', 0) < 40]),
    }

stocks = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428',
    '2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
stocks = [s for s in stocks if s not in blacklist]

print('='*70)
print(' Q1 2026 技術+法人 迭代優化')
print('='*70)

inst_map = load_inst()

# Iteration 1: Baseline
print('\n[ Iteration 1: Baseline ]')
params1 = {'max_rsi': 65, 'min_atr': 30, 'min_vif': 0, 'inst_days': 3, 'inst_min': 1}
trades1 = bt(params1, stocks, inst_map)
wins1 = len([t for t in trades1 if t['ret'] > 0])
wr1 = wins1 / len(trades1) * 100 if trades1 else 0
fail1 = analyze_failures(trades1)
print('  Signals: %d, WR: %.1f%%, Avg: %+.2f%%' % (len(trades1), wr1, np.mean([t['ret'] for t in trades1]) if trades1 else 0))
print('  Failures: High RSI=%d, Low VIF=%d, Low ATR=%d' % (fail1.get('high_rsi',0), fail1.get('low_vif',0), fail1.get('low_atr',0)))

# Iteration 2: Relax RSI
print('\n[ Iteration 2: Relax RSI ]')
params2 = {'max_rsi': 68, 'min_atr': 30, 'min_vif': 0, 'inst_days': 3, 'inst_min': 1}
trades2 = bt(params2, stocks, inst_map)
wins2 = len([t for t in trades2 if t['ret'] > 0])
wr2 = wins2 / len(trades2) * 100 if trades2 else 0
fail2 = analyze_failures(trades2)
print('  Signals: %d, WR: %.1f%%, Avg: %+.2f%%' % (len(trades2), wr2, np.mean([t['ret'] for t in trades2]) if trades2 else 0))
print('  Failures: High RSI=%d, Low VIF=%d, Low ATR=%d' % (fail2.get('high_rsi',0), fail2.get('low_vif',0), fail2.get('low_atr',0)))

# Iteration 3: Relax ATR
print('\n[ Iteration 3: Relax ATR ]')
params3 = {'max_rsi': 65, 'min_atr': 25, 'min_vif': 0, 'inst_days': 3, 'inst_min': 1}
trades3 = bt(params3, stocks, inst_map)
wins3 = len([t for t in trades3 if t['ret'] > 0])
wr3 = wins3 / len(trades3) * 100 if trades3 else 0
fail3 = analyze_failures(trades3)
print('  Signals: %d, WR: %.1f%%, Avg: %+.2f%%' % (len(trades3), wr3, np.mean([t['ret'] for t in trades3]) if trades3 else 0))
print('  Failures: High RSI=%d, Low VIF=%d, Low ATR=%d' % (fail3.get('high_rsi',0), fail3.get('low_vif',0), fail3.get('low_atr',0)))

# Iteration 4: Inst 1 day
print('\n[ Iteration 4: Inst 1 day ]')
params4 = {'max_rsi': 65, 'min_atr': 30, 'min_vif': 0, 'inst_days': 1, 'inst_min': 1}
trades4 = bt(params4, stocks, inst_map)
wins4 = len([t for t in trades4 if t['ret'] > 0])
wr4 = wins4 / len(trades4) * 100 if trades4 else 0
fail4 = analyze_failures(trades4)
print('  Signals: %d, WR: %.1f%%, Avg: %+.2f%%' % (len(trades4), wr4, np.mean([t['ret'] for t in trades4]) if trades4 else 0))
print('  Failures: High RSI=%d, Low VIF=%d, Low ATR=%d' % (fail4.get('high_rsi',0), fail4.get('low_vif',0), fail4.get('low_atr',0)))

# Iteration 5: No Inst filter
print('\n[ Iteration 5: No Inst ]')
params5 = {'max_rsi': 65, 'min_atr': 30, 'min_vif': 0, 'inst_days': 0, 'inst_min': 0}
trades5 = bt(params5, stocks, inst_map)
wins5 = len([t for t in trades5 if t['ret'] > 0])
wr5 = wins5 / len(trades5) * 100 if trades5 else 0
fail5 = analyze_failures(trades5)
print('  Signals: %d, WR: %.1f%%, Avg: %+.2f%%' % (len(trades5), wr5, np.mean([t['ret'] for t in trades5]) if trades5 else 0))
print('  Failures: High RSI=%d, Low VIF=%d, Low ATR=%d' % (fail5.get('high_rsi',0), fail5.get('low_vif',0), fail5.get('low_atr',0)))

# Iteration 6: Combined relax
print('\n[ Iteration 6: RSI<68 + ATR>=25 ]')
params6 = {'max_rsi': 68, 'min_atr': 25, 'min_vif': 0, 'inst_days': 3, 'inst_min': 1}
trades6 = bt(params6, stocks, inst_map)
wins6 = len([t for t in trades6 if t['ret'] > 0])
wr6 = wins6 / len(trades6) * 100 if trades6 else 0
fail6 = analyze_failures(trades6)
print('  Signals: %d, WR: %.1f%%, Avg: %+.2f%%' % (len(trades6), wr6, np.mean([t['ret'] for t in trades6]) if trades6 else 0))
print('  Failures: High RSI=%d, Low VIF=%d, Low ATR=%d' % (fail6.get('high_rsi',0), fail6.get('low_vif',0), fail6.get('low_atr',0)))

# Summary
print('\n' + '='*70)
print(' SUMMARY')
print('='*70)
results = [
    ('Iter1: RSI<65+Inst3d', len(trades1), wr1),
    ('Iter2: RSI<68+Inst3d', len(trades2), wr2),
    ('Iter3: RSI<65+ATR>=25+Inst3d', len(trades3), wr3),
    ('Iter4: RSI<65+Inst1d', len(trades4), wr4),
    ('Iter5: No Inst', len(trades5), wr5),
    ('Iter6: RSI<68+ATR>=25+Inst3d', len(trades6), wr6),
]
results.sort(key=lambda x: (x[2], x[1]), reverse=True)
for name, sig, wr in results:
    print('  %s: %d signals, WR=%.1f%%' % (name, sig, wr))

print('\n  Best WR: %s (%.1f%%)' % (max(results, key=lambda x: x[2])[0], max(r[2] for r in results)))
print('  Most Signals: %s (%d)' % (max(results, key=lambda x: x[1])[0], max(r[1] for r in results)))