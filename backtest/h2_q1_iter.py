# -*- coding: utf-8 -*-
"""
H2 2025 + Q1 2026 (2025-07 to 2026-03) - 技術+法人 迭代優化
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

def bt(params, stocks, inst_map, start='2025-07-01', end='2026-03-31'):
    all_trades = []
    for code in stocks:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
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
    if not trades: return {'wr': 0, 'signals': 0, 'avg': 0}
    wins = len([t for t in trades if t['ret'] > 0])
    return {
        'wr': wins / len(trades) * 100,
        'signals': len(trades),
        'avg': np.mean([t['ret'] for t in trades])
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
print(' H2 2025 + Q1 2026 (2025-07 至 2026-03) 技術+法人 迭代優化')
print('='*70)

inst_map = load_inst()

configs = [
    ('RSI<70 No Inst', {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 0}),
    ('RSI<70+Inst1d', {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 1}),
    ('RSI<70+Inst2d', {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 2}),
    ('RSI<70+Inst3d', {'max_rsi': 70, 'min_atr': 0.5, 'inst_days': 3}),
    ('RSI<72+Inst3d', {'max_rsi': 72, 'min_atr': 0.5, 'inst_days': 3}),
    ('RSI<75+Inst3d', {'max_rsi': 75, 'min_atr': 0.5, 'inst_days': 3}),
    ('RSI<70+Inst3d NoATR', {'max_rsi': 70, 'min_atr': 0, 'inst_days': 3}),
    ('RSI<68+Inst3d', {'max_rsi': 68, 'min_atr': 0.5, 'inst_days': 3}),
    ('RSI<65+Inst3d', {'max_rsi': 65, 'min_atr': 0.5, 'inst_days': 3}),
    ('RSI<65+Inst1d', {'max_rsi': 65, 'min_atr': 0.5, 'inst_days': 1}),
]

results = []
for name, params in configs:
    t = bt(params, stocks, inst_map)
    r = analyze(t)
    print('%s: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (name, r['signals'], r['wr'], r['avg']))
    results.append({'name': name, 'signals': r['signals'], 'wr': r['wr'], 'avg': r['avg'], 'params': params})

print('\n' + '='*70)
print(' SUMMARY (Sorted by WR desc)')
print('='*70)
results.sort(key=lambda x: x['wr'], reverse=True)
for r in results:
    print('%s: %d signals, WR=%.1f%%' % (r['name'], r['signals'], r['wr']))

# Best WR with WR>=65
valid = [r for r in results if r['wr'] >= 65]
best_wr = max(results, key=lambda x: x['wr'])
best_bal = max(valid, key=lambda x: x['signals']) if valid else None

print('\n  Best WR: %s (%.1f%%)' % (best_wr['name'], best_wr['wr']))
if best_bal:
    print('  Best Balance (WR>=65): %s (%d signals, WR=%.1f%%)' % (best_bal['name'], best_bal['signals'], best_bal['wr']))
else:
    print('  No config with WR>=65')