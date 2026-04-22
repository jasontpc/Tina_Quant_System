# -*- coding: utf-8 -*-
"""
v3.12 + 三大法人 完整回測
H2 2025 市值前100台股
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
import numpy as np
import time
from datetime import datetime

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# Load institutional data
INST = {}
try:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT symbol, date, foreign_net, trust_net, dealer_net FROM MarketData')
    for sym, date, f_net, t_net, d_net in cur.fetchall():
        if sym not in INST:
            INST[sym] = {}
        INST[sym][date] = (f_net or 0, t_net or 0, d_net or 0)
    conn.close()
    print('Loaded %d symbols from database' % len(INST))
except Exception as e:
    print('DB Error:', e)
    INST = {}

def get_inst(sym, date):
    """Get institutional data for symbol on date"""
    if sym in INST and date in INST[sym]:
        return INST[sym][date]
    if sym in INST:
        for d in sorted(INST[sym].keys(), reverse=True):
            if d <= date:
                return INST[sym][d]
    return (0, 0, 0)

def get_inst_days(sym, date, days=5):
    """Calculate consecutive institutional buying days"""
    f_days, t_days = 0, 0
    for i in range(days):
        d = str((datetime.strptime(date, '%Y-%m-%d') - np.timedelta64(i, 'D')).astype(datetime))
        f_net, t_net, _ = get_inst(sym, d[:10])
        if f_net > 0: f_days += 1
        if t_net > 0: t_days += 1
    return f_days, t_days

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr(h, period=14):
    high, low, close = list(h['High']), list(h['Low']), list(h['Close'])
    tr = [max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])) for i in range(1, len(high))]
    return np.mean(tr[-period:]) if len(tr) >= period else 30

def calc_sc(f_days, t_days, rs, bias, vr):
    """v3.12 scoring system"""
    max_days = max(f_days, t_days)
    inst_sc = 40 if max_days >= 6 else (35 if max_days >= 4 else (25 if max_days == 3 else (10 if max_days >= 1 else 0)))
    inst_sc += 25 if f_days >= 3 and t_days >= 3 else (20 if f_days >= 5 else (15 if t_days >= 5 else (5 if f_days >= 1 or t_days >= 1 else 0)))
    rs_sc = 15 if 50 <= rs <= 70 else (10 if 30 <= rs < 50 else 5)
    bias_sc = 15 if abs(bias) <= 3 else (10 if abs(bias) <= 6 else 5)
    vol_bonus = 15 if vr > 2.5 else (10 if vr > 2.0 else (5 if vr > 1.5 else 0))
    return inst_sc + rs_sc + bias_sc + vol_bonus

def bt(code, start='2025-07-01', end='2025-12-31'):
    try:
        h = yf.Ticker(code+'.TW').history(start=start, end=end)
        if len(h) < 25: return None
        cl, vol = list(h['Close']), list(h['Volume'])
        s = []
        for i in range(25, len(cl)):
            date = str(h.index[i])[:10]
            rs = rsi(cl[:i+1])
            ma20 = np.mean(cl[i-20:i])
            bias = (cl[i] / ma20 - 1) * 100
            atr = calc_atr(h.iloc[:i+1])
            vr = vol[i] / np.mean(vol[i-20:i]) if np.mean(vol[i-20:i]) > 0 else 0

            # v3.12 filters
            if rs >= 78 or cl[i] < ma20: continue
            if atr < 30: continue

            # Get institutional days
            f_days, t_days = get_inst_days(code, date)

            # Calculate score
            sc = calc_sc(f_days, t_days, rs, bias, vr)
            if sc < 72: continue

            entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
            ret = (cl[min(i+6,len(cl)-1)] / entry - 1) * 100 - 0.45
            s.append({'ret': ret, 'score': sc, 'f_days': f_days, 't_days': t_days, 'rs': rs})
        if not s: return None
        w = len([x for x in s if x['ret'] > 0])
        return {
            't': len(s), 'wr': w/len(s)*100,
            'avg': np.mean([x['ret'] for x in s]),
            'avg_score': np.mean([x['score'] for x in s]),
            'avg_f_days': np.mean([x['f_days'] for x in s]),
            'avg_t_days': np.mean([x['t_days'] for x in s])
        }
    except Exception as e:
        return None

# Top 100 stocks
top100 = ['2330','2317','2303','2454','3034','3008','2002','1301','1326','1216',
    '2610','2615','2891','2881','5871','6505','3665','3017','2345','6230',
    '3583','2360','6139','3189','3443','1590','2308','2382','2408','2474',
    '3033','3231','3338','3702','4938','5880','6446','6669','6770',
    '8046','8454','8478','8499','3711','4961','2379','2451','2201','2207',
    '2231','2352','2353','2354','2356','2371','2373','2376','2383','2385',
    '2392','2393','2401','2402','2404','2412','2420','2423','2425','2426',
    '2427','2428','2429','2430','2431','2432','2433','2434','2436','2438',
    '2439','4952','6415','6183']

print('=' * 70)
print(' H2 2025 v3.12 + 三大法人 回測')
print('=' * 70)

results = []
for i, code in enumerate(top100, 1):
    r = bt(code)
    if r:
        results.append({'code': code, **r})
        print('%s: %d signals, WR=%5.1f%%, Score=%.1f, F=%d, T=%d' % (
            code, r['t'], r['wr'], r['avg_score'], r['avg_f_days'], r['avg_t_days']))
    time.sleep(0.1)

# Summary
if results:
    total_t = sum(r['t'] for r in results)
    total_w = sum(r['wr']/100 * r['t'] for r in results)
    print()
    print('=' * 70)
    print(' 總結')
    print('=' * 70)
    print('股票: %d 檔' % len(results))
    print('交易: %d 次' % total_t)
    print('勝率: %5.1f%%' % (total_w/total_t*100))
    print('平均報酬: %+.2f%%' % np.mean([r['avg'] for r in results]))
    print('平均分數: %.1f' % np.mean([r['avg_score'] for r in results]))
    print('平均法人天數: F=%.1f, T=%.1f' % (
        np.mean([r['avg_f_days'] for r in results]),
        np.mean([r['avg_t_days'] for r in results])))

    # Top performers
    results.sort(key=lambda x: -x['wr'])
    print()
    print('勝率 Top 10:')
    for r in results[:10]:
        print('  %s: WR=%5.1f%%, Score=%.1f, F=%d, T=%d' % (
            r['code'], r['wr'], r['avg_score'], r['avg_f_days'], r['avg_t_days']))
