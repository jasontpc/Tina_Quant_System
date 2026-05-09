# -*- coding: utf-8 -*-
"""
Tina v3.x 完整回測腳本
依序測試 v3.0 ~ v3.11 在 H2 2025 和 Q1 2026
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import json
from datetime import datetime

OUTPUT = 'Tina_Quant_System/backtest/v3x_full_results.json'

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def bt(code, start, end):
    try:
        h = yf.Ticker(code+'.TW').history(start=start, end=end)
        if len(h) < 25: return None
        cl = list(h['Close'])
        s = []
        for i in range(25, len(cl)):
            rs = rsi(cl[:i+1])
            ma20 = np.mean(cl[i-20:i])
            if rs >= 78 or cl[i] < ma20: continue
            entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
            ret = (cl[min(i+6,len(cl)-1)] / entry - 1) * 100 - 0.45
            s.append(ret)
        if not s: return None
        w = len([x for x in s if x > 0])
        return {'t': len(s), 'wr': w/len(s)*100, 'avg': np.mean(s)}
    except:
        return None

top100 = ['2330','2317','2303','2454','3034','3008','2002','1301','1326','1216',
    '2610','2615','2891','2881','5871','6505','3665','3017','2345','6230',
    '3583','2360','6139','3189','3443','1590','2308','2382','2408','2474',
    '3033','3231','3338','3702','4938','5880','6446','6669','6770',
    '8046','8454','8478','8499','3711','4961','2379','2451','2201','2207',
    '2231','2352','2353','2354','2356','2371','2373','2376','2383','2385',
    '2392','2393','2401','2402','2404','2412','2420','2423','2425','2426',
    '2427','2428','2429','2430','2431','2432','2433','2434','2436','2438',
    '2439','4952','6415','6183']

results = {'H2_2025': {}, 'Q1_2026': {}}

# H2 2025 (July - Dec 2025)
print('=' * 60)
print(' H2 2025 回測中...')
print('=' * 60)
for code in top100:
    r = bt(code, '2025-07-01', '2025-12-31')
    if r:
        results['H2_2025'][code] = r
        print('%s: %d signals, WR=%5.1f%%' % (code, r['t'], r['wr']))

# Q1 2026 (Jan - Mar 2026)
print('=' * 60)
print(' Q1 2026 回測中...')
print('=' * 60)
for code in top100:
    r = bt(code, '2026-01-01', '2026-03-31')
    if r:
        results['Q1_2026'][code] = r
        print('%s: %d signals, WR=%5.1f%%' % (code, r['t'], r['wr']))

# Summary
print('=' * 60)
print(' 總結')
print('=' * 60)

for period, data in results.items():
    if data:
        total_t = sum(r['t'] for r in data.values())
        total_w = sum(r['wr']/100 * r['t'] for r in data.values())
        wr = total_w/total_t*100 if total_t > 0 else 0
        avg = np.mean([r['avg'] for r in data.values()])
        print('%s: %d stocks, %d signals, WR=%5.1f%%, Avg=%+6.2f%%' % (
            period, len(data), total_t, wr, avg))

# Save
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('Results saved to', OUTPUT)
