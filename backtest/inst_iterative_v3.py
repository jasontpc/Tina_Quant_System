# -*- coding: utf-8 -*-
"""
Q1 2026 Backtest with Institutional Data + Iterative Optimization
Fixed: Remove min_score requirement
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import pandas as pd
import time

DB = 'skills/stock-analyzer/scripts/tina_master.db'

def load_inst_data():
    inst_map = {}
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
    for sym, date, f_net, t_net in cur.fetchall():
        if sym not in inst_map:
            inst_map[sym] = {}
        inst_map[sym][date] = (f_net or 0, t_net or 0)
    conn.close()
    return inst_map

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

def backtest(params, stocks, inst_map, use_inst=False, inst_days=3):
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
                
                # Filters only - no score requirement
                if rs >= params.get('max_rsi', 65): continue
                if cl[i] < ma20: continue
                if atr < params.get('min_atr', 30): continue
                
                # Optional institutional filter
                inst_pass = False
                if use_inst and code in inst_map:
                    f_days, t_days = 0, 0
                    for d in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            f_net, t_net = inst_map[code][dt]
                            if f_net > 0: f_days += 1
                            if t_net > 0: t_days += 1
                    max_days = max(f_days, t_days) if f_days or t_days else 0
                    if inst_days == 4:
                        inst_pass = (f_days >= 2 and t_days >= 2)
                    else:
                        inst_pass = (max_days >= inst_days)
                elif not use_inst:
                    inst_pass = True
                else:
                    inst_pass = False
                
                if not inst_pass: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6,len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'rsi': rs, 'vr': vr, 'code': code})
        except:
            pass
        time.sleep(0.1)
    return all_trades

stocks = ['2330','2317','2303','2454','3034','3008','2002','1301','1326','1216',
    '2610','2615','2891','2881','5871','6505','3665','3017','2345','6230',
    '3583','2360','6139','3189','3443','1590','2308','2382','2408','2474',
    '3033','3231','3338','3702','4938','5880','6446','6669','6770','8046',
    '8454','8478','8499','3711','4961','2379','2451','2201','2207','2231',
    '2352','2353','2354','2356','2371','2373','2376','2383','2385','2392',
    '2393','2401','2402','2404','2412','2420','2423','2425','2426','2427',
    '2428','2429','2430','2431','2432','2433','2434','2436','2438','2439',
    '4952','6415','6183']

blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
stocks = [s for s in stocks if s not in blacklist]

print('='*70)
print(' Q1 2026 法人資金流向 + 技術面 迭代優化 (v3)')
print('='*70)

print('Loading institutional data...')
inst_map = load_inst_data()
print('Loaded %d symbols' % len(inst_map))

configs = [
    ('No Inst, RSI<65', {'max_rsi': 65, 'min_atr': 30}, False, 3),
    ('Inst 3days, RSI<65', {'max_rsi': 65, 'min_atr': 30}, True, 3),
    ('Inst 4days, RSI<65', {'max_rsi': 65, 'min_atr': 30}, True, 4),
    ('Inst 5days, RSI<65', {'max_rsi': 65, 'min_atr': 30}, True, 5),
    ('Inst 3days, RSI<62', {'max_rsi': 62, 'min_atr': 30}, True, 3),
    ('Inst 4days, RSI<62', {'max_rsi': 62, 'min_atr': 30}, True, 4),
]

print()
results = []
for name, params, use_inst, inst_days in configs:
    trades = backtest(params, stocks, inst_map, use_inst, inst_days)
    if trades:
        wins = len([t for t in trades if t['ret'] > 0])
        wr = wins / len(trades) * 100
        avg = np.mean([t['ret'] for t in trades])
        print('%s: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (name, len(trades), wr, avg))
        results.append({'name': name, 'wr': wr, 'signals': len(trades), 'avg': avg})
    else:
        print('%s: 0 signals' % name)
        results.append({'name': name, 'wr': 0, 'signals': 0, 'avg': 0})

best = max(results, key=lambda x: x['wr'])
print()
print('='*70)
print(' BEST: %s, WR=%.1f%%, Signals=%d' % (best['name'], best['wr'], best['signals']))
print('='*70)

if best['wr'] >= 65:
    print('TARGET REACHED: %.1f%% >= 65%%' % best['wr'])
else:
    print('TARGET NOT REACHED: %.1f%% < 65%%' % best['wr'])