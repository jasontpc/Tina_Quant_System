# -*- coding: utf-8 -*-
"""
Iterative Backtest Optimization
每次修正後自動回測，勝率變差則回溯
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

def backtest(code, params, start='2026-01-01', end='2026-03-31'):
    try:
        h = yf.Ticker(code+'.TW').history(start=start, end=end)
        if len(h) < 25: return None
        cl, vol = list(h['Close']), list(h['Volume'])
        trades = []
        for i in range(25, len(cl)):
            rs = rsi(cl[:i+1])
            ma20 = np.mean(cl[i-20:i])
            bias = (cl[i] / ma20 - 1) * 100
            atr = calc_atr(h, i)
            vr = vol[i] / np.mean(vol[i-20:i]) if np.mean(vol[i-20:i]) > 0 else 0
            
            # Dynamic parameters
            if rs >= params.get('max_rsi', 78): continue
            if cl[i] < ma20: continue
            if atr < params.get('min_atr', 30): continue
            if bias > params.get('max_bias', 99): continue
            if vr < params.get('min_vif', 0): continue
            
            # Score calculation
            rs_sc = 15 if 50 <= rs <= 70 else (10 if 30 <= rs < 50 else 5)
            bias_sc = 15 if abs(bias) <= 3 else (10 if abs(bias) <= 6 else 5)
            vol_sc = 15 if vr > 2.5 else (10 if vr > 2.0 else (5 if vr > 1.5 else 0))
            sc = rs_sc + bias_sc + vol_sc + params.get('base_score', 40)
            
            if sc < params.get('min_score', 72): continue
            
            entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
            exit_p = cl[min(i+6,len(cl)-1)]
            ret = (exit_p / entry - 1) * 100 - 0.45
            
            trades.append({'ret': ret, 'rsi': rs, 'bias': bias, 'vr': vr, 'atr': atr, 'sc': sc})
        return trades
    except:
        return None

def run_backtest(params, stocks):
    all_trades = []
    for code in stocks:
        trades = backtest(code, params)
        if trades:
            all_trades.extend(trades)
        time.sleep(0.1)
    return all_trades

# Stock list
stocks = ['2330','2317','2303','2454','3034','3008','2002','1301','1326','1216',
    '2610','2615','2891','2881','5871','6505','3665','3017','2345','6230',
    '3583','2360','6139','3189','3443','1590','2308','2382','2408','2474',
    '3033','3231','3338','3702','4938','5880','6446','6669','6770','8046',
    '8454','8478','8499','3711','4961','6230','2379','2451','2201','2207',
    '2231','2352','2353','2354','2356','2371','2373','2376','2383','2385',
    '2392','2393','2401','2402','2404','2412','2420','2423','2425','2426',
    '2427','2428','2429','2430','2431','2432','2433','2434','2436','2438',
    '2439','4952','6415','6183']

# Base v3.12 params
base_params = {
    'min_score': 72,
    'max_rsi': 78,
    'min_atr': 30,
    'max_bias': 99,
    'min_vif': 0,
    'base_score': 40
}

results_log = []

def test_config(name, params):
    trades = run_backtest(params, stocks)
    if not trades:
        return 0, 0, []
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    wr = len(wins) / len(trades) * 100
    avg = np.mean([t['ret'] for t in trades])
    
    # Failure analysis
    failure_analysis = {}
    if losses:
        failure_analysis['high_rsi'] = len([t for t in losses if t['rsi'] >= 65])
        failure_analysis['high_bias'] = len([t for t in losses if t['bias'] > 6])
        failure_analysis['low_vif'] = len([t for t in losses if t['vr'] < 1.5])
    
    print(f"\n{'='*60}")
    print(f" {name}")
    print(f"{'='*60}")
    print(f" Signals: {len(trades)}, WR: {wr:.1f}%, Avg: {avg:+.2f}%")
    if failure_analysis:
        print(f" High RSI: {failure_analysis['high_rsi']}, High Bias: {failure_analysis['high_bias']}, Low VIF: {failure_analysis['low_vif']}")
    
    return wr, len(trades), failure_analysis

# Iteration 1: Base v3.12
print("\n" + "="*70)
print(" ITERATION 1: v3.12 Base")
print("="*70)
best_wr, best_signals, best_params = base_params.copy(), None, None
best_name = "v3.12 Base"

wr1, sig1, fail1 = test_config("v3.12 Base", base_params)
results_log.append({'iter': 1, 'name': 'v3.12 Base', 'wr': wr1, 'signals': sig1, 'params': base_params.copy()})

# Iteration 2: Add VIF >= 1.2
params2 = base_params.copy()
params2['min_vif'] = 1.2
wr2, sig2, fail2 = test_config("VIF >= 1.2", params2)
results_log.append({'iter': 2, 'name': 'VIF>=1.2', 'wr': wr2, 'signals': sig2, 'params': params2.copy()})

if wr2 > wr1:
    best_wr, best_signals, best_params = wr2, sig2, params2
    best_name = "VIF>=1.2"
    print(f" >>> IMPROVED! Using VIF>=1.2")

# Iteration 3: VIF >= 1.5
params3 = base_params.copy()
params3['min_vif'] = 1.5
wr3, sig3, fail3 = test_config("VIF >= 1.5", params3)
results_log.append({'iter': 3, 'name': 'VIF>=1.5', 'wr': wr3, 'signals': sig3, 'params': params3.copy()})

if wr3 > best_wr:
    best_wr, best_signals, best_params = wr3, sig3, params3
    best_name = "VIF>=1.5"
    print(f" >>> IMPROVED! Using VIF>=1.5")

# Iteration 4: RSI < 65
params4 = base_params.copy()
params4['max_rsi'] = 65
wr4, sig4, fail4 = test_config("RSI < 65", params4)
results_log.append({'iter': 4, 'name': 'RSI<65', 'wr': wr4, 'signals': sig4, 'params': params4.copy()})

if wr4 > best_wr:
    best_wr, best_signals, best_params = wr4, sig4, params4
    best_name = "RSI<65"
    print(f" >>> IMPROVED! Using RSI<65")

# Iteration 5: VIF >= 1.2 + RSI < 65
params5 = base_params.copy()
params5['min_vif'] = 1.2
params5['max_rsi'] = 65
wr5, sig5, fail5 = test_config("VIF>=1.2 + RSI<65", params5)
results_log.append({'iter': 5, 'name': 'VIF>=1.2 + RSI<65', 'wr': wr5, 'signals': sig5, 'params': params5.copy()})

if wr5 > best_wr:
    best_wr, best_signals, best_params = wr5, sig5, params5
    best_name = "VIF>=1.2 + RSI<65"
    print(f" >>> IMPROVED! Using combined")

# Iteration 6: Bias < 6%
params6 = base_params.copy()
params6['max_bias'] = 6
wr6, sig6, fail6 = test_config("Bias < 6%", params6)
results_log.append({'iter': 6, 'name': 'Bias<6%', 'wr': wr6, 'signals': sig6, 'params': params6.copy()})

if wr6 > best_wr:
    best_wr, best_signals, best_params = wr6, sig6, params6
    best_name = "Bias<6%"
    print(f" >>> IMPROVED! Using Bias<6%")

# Iteration 7: VIF>=1.2 + RSI<65 + Bias<6%
params7 = base_params.copy()
params7['min_vif'] = 1.2
params7['max_rsi'] = 65
params7['max_bias'] = 6
wr7, sig7, fail7 = test_config("Combined (VIF+RSI+Bias)", params7)
results_log.append({'iter': 7, 'name': 'Combined', 'wr': wr7, 'signals': sig7, 'params': params7.copy()})

if wr7 > best_wr:
    best_wr, best_signals, best_params = wr7, sig7, params7
    best_name = "Combined"
    print(f" >>> IMPROVED! Using Combined")

# Final summary
print("\n" + "="*70)
print(" FINAL RESULT")
print("="*70)
print(f" Best Config: {best_name}")
print(f" Win Rate: {best_wr:.1f}%")
print(f" Signals: {best_signals}")
print(f" Parameters: {best_params}")
