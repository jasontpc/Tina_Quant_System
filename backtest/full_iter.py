# -*- coding: utf-8 -*-
"""
Q1 2026 - 技術+法人 完整迭代優化 (Top 200)
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

def calc_atr_pct(h, i):
    high = list(h['High'].iloc[max(0,i-14):i+1])
    low = list(h['Low'].iloc[max(0,i-14):i+1])
    close = list(h['Close'].iloc[max(0,i-14):i+1])
    tr = [max(high[j]-low[j], abs(high[j]-close[j-1]), abs(low[j]-close[j-1])) for j in range(1, len(high))]
    atr = np.mean(tr[-14:]) if len(tr) >= 14 else 30
    return (atr / close[-1]) * 100

def bt(params, stocks, inst_map):
    all_trades = []
    for code in stocks:
        try:
            h = yf.Ticker(code+'.TW').history(start='2026-01-01', end='2026-03-31')
            if len(h) < 26: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)-1):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                atr_pct = calc_atr_pct(h, i)
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                date_str = str(h.index[i])[:10]
                
                if rs >= params.get('max_rsi', 70): continue
                if cl[i] < ma20: continue
                if atr_pct < params.get('min_atr', 0.5): continue
                
                # Institutional filter
                inst_days = params.get('inst_days', 0)
                if inst_days > 0 and code in inst_map:
                    f_days, t_days = 0, 0
                    for d in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                elif inst_days > 0:
                    continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6,len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'rsi': rs, 'atr': atr_pct, 'vr': vr, 'code': code})
        except:
            pass
        time.sleep(0.05)
    return all_trades

def analyze(trades):
    if not trades: return {'wr': 0, 'signals': 0, 'avg': 0, 'fail': {}}
    wins = len([t for t in trades if t['ret'] > 0])
    losses = [t for t in trades if t['ret'] <= 0]
    return {
        'wr': wins / len(trades) * 100,
        'signals': len(trades),
        'avg': np.mean([t['ret'] for t in trades]),
        'fail': {
            'high_rsi': len([t for t in losses if t['rsi'] >= 60]),
            'low_atr': len([t for t in losses if t['atr'] < 1.0]),
            'low_vr': len([t for t in losses if t.get('vr', 0) < 1.0]),
        }
    }

stocks = ['2330','2317','2303','2454','3034','3008','2002','1301','1326','1216',
    '2610','2615','2891','2881','5871','6505','3665','3017','2345','6230',
    '3583','2360','6139','3189','3443','1590','2308','2382','2408','2474',
    '3033','3231','3338','3702','4938','5880','6446','6669','6770','8046',
    '8454','8478','8499','3711','4961','6230','2379','2451','2201','2207',
    '2231','2352','2353','2354','2356','2371','2373','2376','2383','2385',
    '2392','2393','2401','2402','2404','2412','2420','2423','2425','2426',
    '2427','2428','2429','2430','2431','2432','2433','2434','2436','2438',
    '2439','4952','6415','6183','2618','2630','2892','2884','2886','2887',
    '2890','5876','5886','6005','6509','8008','8049','2453','2498','2504',
    '2520','2527','2530','2535','2542','2597','2722','2723','2724','2809',
    '2820','2832','2834','2836','2845','2850','2855','2867','2880','2883',
    '2885','2888','2897','5875','5877','5888','6004','6011','6012','6036',
    '6055','6172','6177','6191','6192','6196','6201','6202','6206','6209',
    '6213','6214','6216','6222','6223','6224','6225','6226','6227','6231',
    '6235','6237','6238','6239','6240','6257','6269','6270','6274','6275',
    '6276','6277','6278','6279','6281','6283','6285','6289','6290','6292']

blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
stocks = [s for s in stocks if s not in blacklist]

print('='*70)
print(' Q1 2026 Top200 技術+法人 迭代優化')
print('='*70)

inst_map = load_inst()

# Baseline
print('\n[ Baseline ]')
p1 = {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 0}
t1 = bt(p1, stocks, inst_map)
r1 = analyze(t1)
print('  RSI<70, No Inst: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (r1['signals'], r1['wr'], r1['avg']))

# With Institutional
print('\n[ + Institutional 3days ]')
p2 = {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 3}
t2 = bt(p2, stocks, inst_map)
r2 = analyze(t2)
print('  RSI<70 + Inst3d: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (r2['signals'], r2['wr'], r2['avg']))

# Relax RSI
print('\n[ Relax RSI<72 ]')
p3 = {'max_rsi': 72, 'min_atr': 0.5, 'inst_days': 3}
t3 = bt(p3, stocks, inst_map)
r3 = analyze(t3)
print('  RSI<72 + Inst3d: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (r3['signals'], r3['wr'], r3['avg']))

# Relax RSI<75
print('\n[ Relax RSI<75 ]')
p4 = {'max_rsi': 75, 'min_atr': 0.5, 'inst_days': 3}
t4 = bt(p4, stocks, inst_map)
r4 = analyze(t4)
print('  RSI<75 + Inst3d: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (r4['signals'], r4['wr'], r4['avg']))

# No ATR filter
print('\n[ No ATR filter ]')
p5 = {'max_rsi': 70, 'min_atr': 0, 'inst_days': 3}
t5 = bt(p5, stocks, inst_map)
r5 = analyze(t5)
print('  RSI<70 + Inst3d (No ATR): %d signals, WR=%.1f%%, Avg=%+.2f%%' % (r5['signals'], r5['wr'], r5['avg']))

# Inst 1 day
print('\n[ Inst 1 day ]')
p6 = {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 1}
t6 = bt(p6, stocks, inst_map)
r6 = analyze(t6)
print('  RSI<70 + Inst1d: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (r6['signals'], r6['wr'], r6['avg']))

# Inst 2 days
print('\n[ Inst 2 days ]')
p7 = {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 2}
t7 = bt(p7, stocks, inst_map)
r7 = analyze(t7)
print('  RSI<70 + Inst2d: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (r7['signals'], r7['wr'], r7['avg']))

# Summary
print('\n' + '='*70)
print(' SUMMARY (Sorted by WR desc)')
print('='*70)
results = [
    ('RSI<70 No Inst', r1['signals'], r1['wr']),
    ('RSI<70+Inst3d', r2['signals'], r2['wr']),
    ('RSI<72+Inst3d', r3['signals'], r3['wr']),
    ('RSI<75+Inst3d', r4['signals'], r4['wr']),
    ('RSI<70+Inst3d NoATR', r5['signals'], r5['wr']),
    ('RSI<70+Inst1d', r6['signals'], r6['wr']),
    ('RSI<70+Inst2d', r7['signals'], r7['wr']),
]
results.sort(key=lambda x: x[2], reverse=True)
for name, sig, wr in results:
    print('  %s: %d signals, WR=%.1f%%' % (name, sig, wr))

# Best by WR
best_wr = max(results, key=lambda x: x[2])
# Best by Signals with WR>=65
valid = [r for r in results if r[2] >= 65]
best_bal = max(valid, key=lambda x: x[1]) if valid else None

print('\n  Best WR: %s (%.1f%%)' % (best_wr[0], best_wr[2]))
if best_bal:
    print('  Best Balance (WR>=65): %s (%d signals, WR=%.1f%%)' % (best_bal[0], best_bal[1], best_bal[2]))
else:
    print('  No config with WR>=65')