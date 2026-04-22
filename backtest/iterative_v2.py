# -*- coding: utf-8 -*-
"""
Iterative Backtest Optimization - Target 65% WR
自動迭代直到勝率達到 65%
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import time
import json

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

def backtest(params, stocks, start='2026-01-01', end='2026-03-31'):
    all_trades = []
    for code in stocks:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 25: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-20:i])
                bias = (cl[i] / ma20 - 1) * 100
                atr = calc_atr(h, i)
                vr = vol[i] / np.mean(vol[i-20:i]) if np.mean(vol[i-20:i]) > 0 else 0
                
                if rs >= params.get('max_rsi', 78): continue
                if cl[i] < ma20: continue
                if atr < params.get('min_atr', 30): continue
                if bias > params.get('max_bias', 99): continue
                if vr < params.get('min_vif', 0): continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6,len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'rsi': rs, 'bias': bias, 'vr': vr, 'atr': atr, 'code': code})
        except:
            pass
        time.sleep(0.1)
    return all_trades

def analyze_failures(trades):
    losses = [t for t in trades if t['ret'] <= 0]
    if not losses: return {}
    
    return {
        'high_rsi': len([t for t in losses if t['rsi'] >= 60]),
        'high_bias': len([t for t in losses if t['bias'] > 5]),
        'low_vif': len([t for t in losses if t['vr'] < 1.5]),
        'low_atr': len([t for t in losses if t['atr'] < 40]),
        'total_losses': len(losses)
    }

def run_test(name, params, stocks):
    trades = backtest(params, stocks)
    if not trades: return 0, 0, {}
    
    wins = [t for t in trades if t['ret'] > 0]
    wr = len(wins) / len(trades) * 100
    avg = np.mean([t['ret'] for t in trades])
    failures = analyze_failures(trades)
    
    print('  [TEST] %s: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (name, len(trades), wr, avg))
    
    return wr, len(trades), failures

# Stock list (top 200)
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

# Blacklist
blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
stocks = [s for s in stocks if s not in blacklist]

print('='*70)
print(' ITERATIVE OPTIMIZATION - TARGET 65% WR')
print('='*70)

# Baseline
baseline = {
    'max_rsi': 65,
    'min_atr': 30,
    'max_bias': 99,
    'min_vif': 0
}

wr, signals, failures = run_test('Baseline (RSI<65)', baseline, stocks)
print('='*70)
print(' Baseline Result: WR=%.1f%%, Signals=%d' % (wr, signals))
print('='*70)

best_params = baseline.copy()
best_wr = wr
iterations = []

# Iteration loop
print()
print('Starting iterative optimization...')
print()

iteration = 1
while best_wr < 65 and iteration <= 20:
    print('--- Iteration %d ---' % iteration)
    
    improved = False
    
    # Test variations
    tests = [
        ('RSI<62', {'max_rsi': 62, 'min_atr': 30, 'max_bias': 99, 'min_vif': 0}),
        ('RSI<60', {'max_rsi': 60, 'min_atr': 30, 'max_bias': 99, 'min_vif': 0}),
        ('VIF>=1.0', {'max_rsi': 65, 'min_atr': 30, 'max_bias': 99, 'min_vif': 1.0}),
        ('VIF>=1.2', {'max_rsi': 65, 'min_atr': 30, 'max_bias': 99, 'min_vif': 1.2}),
        ('Bias<8%', {'max_rsi': 65, 'min_atr': 30, 'max_bias': 8, 'min_vif': 0}),
        ('Bias<6%', {'max_rsi': 65, 'min_atr': 30, 'max_bias': 6, 'min_vif': 0}),
        ('ATR>=40', {'max_rsi': 65, 'min_atr': 40, 'max_bias': 99, 'min_vif': 0}),
        ('ATR>=50', {'max_rsi': 65, 'min_atr': 50, 'max_bias': 99, 'min_vif': 0}),
        ('RSI<63 + VIF>=1.0', {'max_rsi': 63, 'min_atr': 30, 'max_bias': 99, 'min_vif': 1.0}),
        ('RSI<65 + Bias<8%', {'max_rsi': 65, 'min_atr': 30, 'max_bias': 8, 'min_vif': 0}),
        ('RSI<62 + ATR>=40', {'max_rsi': 62, 'min_atr': 40, 'max_bias': 99, 'min_vif': 0}),
        ('VIF>=1.0 + ATR>=40', {'max_rsi': 65, 'min_atr': 40, 'max_bias': 99, 'min_vif': 1.0}),
    ]
    
    for name, params in tests:
        wr, sig, _ = run_test(name, params, stocks)
        if wr > best_wr:
            best_wr = wr
            best_params = params.copy()
            improved = True
            print('  >>> NEW BEST: %s, WR=%.1f%%' % (name, wr))
    
    if not improved:
        print('  No improvement found. Best WR=%.1f%%' % best_wr)
        break
    
    iteration += 1
    print()

# Final report
print('='*70)
print(' FINAL RESULT')
print('='*70)
print(' Best Win Rate: %.1f%%' % best_wr)
print(' Best Parameters:', best_params)
print(' Iteration Count: %d' % (iteration - 1))
print('='*70)