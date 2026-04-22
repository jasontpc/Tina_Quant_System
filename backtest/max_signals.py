# -*- coding: utf-8 -*-
"""
Q1 2026 - Iterative Optimization to Maximize Signals
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
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
                
                if rs >= params.get('max_rsi', 65): continue
                if cl[i] < ma20: continue
                if atr < params.get('min_atr', 30): continue
                
                # Score calculation
                rs_sc = 15 if 50 <= rs <= 70 else 10
                sc = rs_sc + 40  # base score
                
                if params.get('min_score', 0) > 0 and sc < params['min_score']: continue
                
                # VIF check
                if params.get('min_vif', 0) > 0 and vr < params['min_vif']: continue
                
                # Institutional filter
                if use_inst and code in inst_map:
                    f_days, t_days = 0, 0
                    for d in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                elif use_inst:
                    continue
                
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
print(' Q1 2026 信號數量優化迭代')
print('='*70)

inst_map = load_inst()
print('法人資料: %d 檔股票\n' % len(inst_map))

configs = [
    # Baseline
    ('Base RSI<65', {'max_rsi': 65, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, False, 3),
    
    # Relax RSI
    ('RSI<68', {'max_rsi': 68, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, False, 3),
    ('RSI<70', {'max_rsi': 70, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, False, 3),
    ('RSI<72', {'max_rsi': 72, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, False, 3),
    
    # Relax ATR
    ('ATR>=25', {'max_rsi': 65, 'min_atr': 25, 'min_score': 0, 'min_vif': 0}, False, 3),
    ('ATR>=20', {'max_rsi': 65, 'min_atr': 20, 'min_score': 0, 'min_vif': 0}, False, 3),
    
    # With Institutional
    ('Inst 3d', {'max_rsi': 65, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, True, 3),
    ('Inst 2d', {'max_rsi': 65, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, True, 2),
    ('Inst 1d', {'max_rsi': 65, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, True, 1),
    
    # Relax + Inst
    ('RSI<68 + Inst 2d', {'max_rsi': 68, 'min_atr': 30, 'min_score': 0, 'min_vif': 0}, True, 2),
    ('ATR>=25 + Inst 1d', {'max_rsi': 65, 'min_atr': 25, 'min_score': 0, 'min_vif': 0}, True, 1),
    ('RSI<70 + ATR>=25', {'max_rsi': 70, 'min_atr': 25, 'min_score': 0, 'min_vif': 0}, False, 3),
    
    # VIF relaxed
    ('VIF>=1.0', {'max_rsi': 65, 'min_atr': 30, 'min_score': 0, 'min_vif': 1.0}, False, 3),
    ('VIF>=0.8', {'max_rsi': 65, 'min_atr': 30, 'min_score': 0, 'min_vif': 0.8}, False, 3),
]

results = []
for name, params, use_inst, inst_days in configs:
    trades = backtest(params, stocks, inst_map, use_inst, inst_days)
    if trades:
        wins = len([t for t in trades if t['ret'] > 0])
        wr = wins / len(trades) * 100
        avg = np.mean([t['ret'] for t in trades])
        print('%s: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (name, len(trades), wr, avg))
        results.append({'name': name, 'wr': wr, 'signals': len(trades), 'avg': avg, 'params': params})
    else:
        print('%s: 0 signals' % name)
        results.append({'name': name, 'wr': 0, 'signals': 0, 'avg': 0, 'params': params})

print()
print('='*70)
print(' 結果排序 (按信號數)')
print('='*70)
results.sort(key=lambda x: x['signals'], reverse=True)
for r in results:
    print('%s: %d signals, WR=%.1f%%' % (r['name'], r['signals'], r['wr']))

# Best by signals and WR>=65
print()
print('='*70)
print(' 最佳平衡 (WR>=65 且信號數最多)')
print('='*70)
valid = [r for r in results if r['wr'] >= 65 and r['signals'] > 0]
if valid:
    best = max(valid, key=lambda x: x['signals'])
    print(' %s: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (best['name'], best['signals'], best['wr'], best['avg']))
else:
    print(' 無配置同時滿足 WR>=65')
    best = max(results, key=lambda x: x['signals'])
    print(' 最高信號: %s: %d signals, WR=%.1f%%' % (best['name'], best['signals'], best['wr']))