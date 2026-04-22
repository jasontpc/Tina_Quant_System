# -*- coding: utf-8 -*-
"""
Analyze the 14 losing signals from v3.12
Find common patterns/characteristics
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
from datetime import datetime

DB = 'skills/stock-analyzer/scripts/tina_master.db'
START = '2026-01-01'
END = '2026-04-22'

INST = {}

BLACKLIST = ['1590', '2308']

def load_inst():
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute('SELECT symbol, date, foreign_consecutive, trust_consecutive FROM MarketData')
        for sym, date, fc, tc in cur.fetchall():
            if sym not in INST: INST[sym] = {}
            INST[sym][date] = (fc or 0, tc or 0)
        conn.close()
    except: pass

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_sc(f_days, t_days, rs, bias, vr):
    max_days = max(f_days, t_days)
    inst_sc = 40 if max_days >= 6 else (35 if max_days >= 4 else (25 if max_days == 3 else (10 if max_days >= 1 else 0)))
    inst_sc += 25 if f_days >= 3 and t_days >= 3 else (20 if f_days >= 5 else (15 if t_days >= 5 else (5 if f_days >= 1 or t_days >= 1 else 0)))
    rs_sc = 15 if 50 <= rs <= 70 else (10 if 30 <= rs < 50 else 5)
    bias_sc = 15 if abs(bias) <= 3 else (10 if abs(bias) <= 6 else 5)
    vol_bonus = 15 if vr > 2.5 else (10 if vr > 2.0 else (5 if vr > 1.5 else 0))
    return inst_sc + rs_sc + bias_sc + vol_bonus

def get_inst(sym, date):
    if sym in INST and date in INST[sym]: return INST[sym][date]
    if sym in INST:
        for d in sorted(INST[sym].keys(), reverse=True):
            if d <= date: return INST[sym][d]
    return (0, 0)

def calc_atr(h, period=14):
    high = list(h['High'])
    low = list(h['Low'])
    close = list(h['Close'])
    tr = []
    for i in range(1, len(high)):
        tr.append(max(high[i] - low[i],
                      abs(high[i] - close[i-1]),
                      abs(low[i] - close[i-1])))
    if len(tr) < period: return 0
    return np.mean(tr[-period:])

def calc_adx(h, period=14):
    high = list(h['High'])
    low = list(h['Low'])
    close = list(h['Close'])
    plus_dm, minus_dm = [], []
    for i in range(1, len(high)):
        h_diff, l_diff = high[i] - high[i-1], low[i-1] - low[i]
        plus_dm.append(h_diff if h_diff > l_diff and h_diff > 0 else 0)
        minus_dm.append(l_diff if l_diff > h_diff and l_diff > 0 else 0)
    atr = calc_atr(h)
    if atr == 0: return 20
    plus_di = np.mean(plus_dm[-period:]) / atr * 100
    minus_di = np.mean(minus_dm[-period:]) / atr * 100
    if plus_di + minus_di == 0: return 20
    return abs(plus_di - minus_di) / (plus_di + minus_di) * 100

load_inst()

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('SELECT DISTINCT symbol FROM MarketData ORDER BY symbol')
STOCKS = [r[0] for r in cur.fetchall()]
conn.close()

PARAMS = {
    'entry': 72,
    'rsi': 78,
    'momentum': 22,
    'slope': 0.025,
    'atr_min': 30,
    'adx_min': 15,
    'vif_min_adx_high': 1.5,
}

all_losses = []

for sym in STOCKS:
    if sym in BLACKLIST:
        continue
        
    try:
        t = yf.Ticker(sym + '.TW')
        h = t.history(start='2025-10-01', end='2026-04-22')
        if len(h) < 100: continue

        dt = [x.strftime('%Y-%m-%d') for x in h.index]
        cl = list(h['Close'])
        vol = list(h['Volume'])

        si = next((i for i, d in enumerate(dt) if d >= START), None)
        ei = max([i for i, d in enumerate(dt) if d <= END]) if any(d <= END for d in dt) else len(dt)-1
        if si is None or ei - si < 20: continue

        for i in range(si + 20, ei + 1):
            if i >= len(cl) or i < 5: continue

            p = cl[i]
            date = dt[i]

            rs_ind = rsi(cl[:i+1])
            if rs_ind > PARAMS['rsi']: continue

            mom = (p / cl[i-5] - 1) * 100 if i >= 5 else 0
            if mom > PARAMS['momentum']: continue

            ma20 = np.mean(cl[i-20:i])
            slope = ma20 - np.mean(cl[i-21:i-1])
            if p < ma20 or slope < PARAMS['slope']: continue

            f_days, t_days = get_inst(sym, date)
            bias = (p / np.mean(cl[i-4:i+1]) - 1) * 100
            vr = vol[i] / np.mean(vol[i-20:i]) if np.mean(vol[i-20:i]) > 0 else 1

            sc = calc_sc(f_days, t_days, rs_ind, bias, vr)
            if sc < PARAMS['entry']: continue

            h_slice = h.iloc[max(0,i-14):i+1]
            atr = calc_atr(h_slice)
            if atr < PARAMS['atr_min']: continue

            adx = calc_adx(h_slice)
            if adx < PARAMS['adx_min']: continue

            if adx > 40 and vr < PARAMS['vif_min_adx_high']:
                continue

            r1 = (cl[i+1] / p - 1) * 100 if i+1 < len(cl) else 0
            r2 = (cl[i+2] / p - 1) * 100 if i+2 < len(cl) else 0
            r3 = (cl[i+3] / p - 1) * 100 if i+3 < len(cl) else 0
            r5 = (cl[i+5] / p - 1) * 100 if i+5 < len(cl) else 0

            all_losses.append({
                'date': date,
                'sym': sym,
                'price': p,
                'score': sc,
                'atr': atr,
                'atr_pct': atr / p * 100,
                'adx': adx,
                'vif': vr,
                'f_days': f_days,
                't_days': t_days,
                'rsi': rs_ind,
                'bias': bias,
                'mom': mom,
                'r1': r1,
                'r2': r2,
                'r3': r3,
                'r5': r5
            })

    except: pass

# Filter to only losses
losses = [l for l in all_losses if l['r5'] <= 0]

print('=' * 70)
print('v3.12 FAILING SIGNALS ANALYSIS')
print('=' * 70)
print()
print('Total Losses: %d out of %d signals' % (len(losses), len(all_losses)))
print('Loss Rate: %.1f%%' % (len(losses) / len(all_losses) * 100 if all_losses else 0))
print()

# Detailed breakdown
print('=' * 70)
print('DETAILED LOSS CHARACTERISTICS')
print('=' * 70)
print()

for idx, l in enumerate(losses):
    print('[%d] %s %s' % (idx+1, l['date'], l['sym']))
    print('  Price: %.1f, Score: %d' % (l['price'], l['score']))
    print('  ATR: %.1f (%.2f%%), ADX: %.1f, VIF: %.2f' % (l['atr'], l['atr_pct'], l['adx'], l['vif']))
    print('  Institutional: F=%d, T=%d' % (l['f_days'], l['t_days']))
    print('  RSI: %.1f, Bias: %.2f%%, Mom: %.2f%%' % (l['rsi'], l['bias'], l['mom']))
    print('  Returns: D1=%+.2f%%, D2=%+.2f%%, D3=%+.2f%%, D5=%+.2f%%' % (
        l['r1'], l['r2'], l['r3'], l['r5']))
    
    # Pattern analysis
    if l['r1'] < -2:
        print('  ⚠️ Pattern: D1 CRASH (>2% drop)')
    elif l['r1'] > 0 and l['r5'] < 0:
        print('  ⚠️ Pattern: D1 PUMP then REVERSAL')
    elif l['adx'] > 40:
        print('  ⚠️ Pattern: ADX EXHAUSTION (>40)')
    elif l['vif'] < 1.5:
        print('  ⚠️ Pattern: LOW VOLUME (VIF < 1.5)')
    else:
        print('  Pattern: GRADUAL DECLINE')
    print()

# Statistical analysis
print('=' * 70)
print('STATISTICAL ANALYSIS OF LOSSES')
print('=' * 70)
print()

# Calculate averages
avg_score = np.mean([l['score'] for l in losses])
avg_atr = np.mean([l['atr'] for l in losses])
avg_atr_pct = np.mean([l['atr_pct'] for l in losses])
avg_adx = np.mean([l['adx'] for l in losses])
avg_vif = np.mean([l['vif'] for l in losses])
avg_f = np.mean([l['f_days'] for l in losses])
avg_t = np.mean([l['t_days'] for l in losses])

print('Average Characteristics of Losing Signals:')
print('  Score: %.1f' % avg_score)
print('  ATR: %.1f (%.2f%%)' % (avg_atr, avg_atr_pct))
print('  ADX: %.1f' % avg_adx)
print('  VIF: %.2f' % avg_vif)
print('  Foreign Days: %.1f' % avg_f)
print('  Trust Days: %.1f' % avg_t)
print()

# Day 1 analysis
d1_crash = sum(1 for l in losses if l['r1'] < -2)
d1_pump = sum(1 for l in losses if l['r1'] > 0)
d1_small = len(losses) - d1_crash - d1_pump

print('Day 1 Pattern Distribution:')
print('  D1 Crash (>2%): %d/%d (%.1f%%)' % (d1_crash, len(losses), d1_crash/len(losses)*100 if losses else 0))
print('  D1 Pump (>0%): %d/%d (%.1f%%)' % (d1_pump, len(losses), d1_pump/len(losses)*100 if losses else 0))
print('  D1 Small: %d/%d (%.1f%%)' % (d1_small, len(losses), d1_small/len(losses)*100 if losses else 0))
print()

# ADX analysis
high_adx = sum(1 for l in losses if l['adx'] > 40)
low_vif = sum(1 for l in losses if l['vif'] < 1.5)

print('ADX Analysis:')
print('  Losses with ADX > 40: %d/%d (%.1f%%)' % (high_adx, len(losses), high_adx/len(losses)*100 if losses else 0))
print()

print('VIF Analysis:')
print('  Losses with VIF < 1.5: %d/%d (%.1f%%)' % (low_vif, len(losses), low_vif/len(losses)*100 if losses else 0))
print()

# Stock concentration
stock_losses = {}
for l in losses:
    sym = l['sym']
    if sym not in stock_losses:
        stock_losses[sym] = 0
    stock_losses[sym] += 1

print('Losses by Stock:')
for sym, cnt in sorted(stock_losses.items(), key=lambda x: -x[1]):
    print('  %s: %d losses' % (sym, cnt))

print()
print('=' * 70)
print('RECOMMENDATIONS')
print('=' * 70)
print()

# Generate recommendations
recommendations = []

if d1_crash / len(losses) > 0.3:
    recommendations.append('Add Day 1 stop-loss rule (stop if D1 < -2%)')

if high_adx / len(losses) > 0.3:
    recommendations.append('Tighten ADX filter: require VIF >= 2.0 when ADX > 40')

if stock_losses:
    worst_stock = max(stock_losses.items(), key=lambda x: x[1])
    if worst_stock[1] >= 3:
        recommendations.append('Consider adding %s to blacklist (has %d losses)' % (worst_stock[0], worst_stock[1]))

if recommendations:
    print('Based on analysis, suggested improvements:')
    for r in recommendations:
        print('  - %s' % r)
else:
    print('No specific pattern found - losses appear random')

print()
print('=' * 70)