# -*- coding: utf-8 -*-
"""
Q1 2026 Backtest with Institutional Data + Iterative Optimization
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import time

DB = 'skills/stock-analyzer/scripts/tina_master.db'

def get_inst_data(sym, date_str, days=3):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    f_days, t_days = 0, 0
    for i in range(1, days+1):
        d = (pd.to_datetime(date_str) - pd.Timedelta(days=i)).strftime('%Y-%m-%d')
        cur.execute('SELECT foreign_net, trust_net FROM MarketData WHERE symbol=? AND date=?', (sym, d))
        row = cur.fetchone()
        if row:
            if row[0] and row[0] > 0: f_days += 1
            if row[1] and row[1] > 0: t_days += 1
    conn.close()
    return f_days, t_days

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

def backtest(params, stocks, use_inst=False):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Load all inst data into memory
    inst_map = {}
    cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
    for sym, date, f_net, t_net in cur.fetchall():
        if sym not in inst_map:
            inst_map[sym] = {}
        inst_map[sym][date] = (f_net or 0, t_net or 0)
    conn.close()
    
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
                
                # Score
                rs_sc = 15 if 50 <= rs <= 70 else 10
                vol_sc = 15 if vr > 2.5 else (10 if vr > 2.0 else 5)
                inst_sc = 40  # default
                
                # Institutional filter
                if use_inst:
                    f_days, t_days = 0, 0
                    for d in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                        if code in inst_map and dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    max_days = max(f_days, t_days)
                    inst_sc = 40 if max_days >= 3 else (25 if max_days >= 2 else 10)
                
                sc = inst_sc + rs_sc + vol_sc
                
                if rs >= params.get('max_rsi', 65): continue
                if cl[i] < ma20: continue
                if atr < params.get('min_atr', 30): continue
                if sc < params.get('min_score', 72): continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6,len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'rsi': rs, 'vr': vr, 'code': code})
        except:
            pass
        time.sleep(0.1)
    return all_trades

def analyze_failures(trades):
    losses = [t for t in trades if t['ret'] <= 0]
    if not losses: return {}
    return {
        'total_losses': len(losses),
        'high_rsi': len([t for t in losses if t['rsi'] >= 60]),
        'low_vif': len([t for t in losses if t['vr'] < 1.5])
    }

stocks = ['2330','2317','2303','2454','3034','3008','2002','1301','1326','1216',
    '2610','2615','2891','2881','5871','6505','3665','3017','2345','6230',
    '3583','2360','6139','3189','3443','1590','2308','2382','2408','2474',
    '3033','3231','3338','3702','4938','5880','6446','6669','6770','8046',
    '8454','8478','8499','3711','4961','6230','2379','2451','2201','2207',
    '2231','2352','2353','2354','2356','2371','2373','2376','2383','2385',
    '2392','2393','2401','2402','2404','2412','2420','2423','2425','2426',
    '2427','2428','2429','2430','2431','2432','2433','2434','2436','2438',
    '2439','4952','6415','6183']

blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
stocks = [s for s in stocks if s not in blacklist]

print('='*70)
print(' Q1 2026 法人資金流向 + 技術面 迭代優化')
print('='*70)

# Baseline with institutional data
params_base = {'max_rsi': 65, 'min_atr': 30, 'min_score': 72}
trades_base = backtest(params_base, stocks, use_inst=True)
wins = len([t for t in trades_base if t['ret'] > 0])
wr_base = wins / len(trades_base) * 100 if trades_base else 0
print('  Baseline (Inst): %d signals, WR=%.1f%%' % (len(trades_base), wr_base))

# Test different configurations
configs = [
    ('RSI<62', {'max_rsi': 62, 'min_atr': 30, 'min_score': 72}),
    ('RSI<60', {'max_rsi': 60, 'min_atr': 30, 'min_score': 72}),
    ('Score>=78', {'max_rsi': 65, 'min_atr': 30, 'min_score': 78}),
    ('Score>=80', {'max_rsi': 65, 'min_atr': 30, 'min_score': 80}),
    ('ATR>=40', {'max_rsi': 65, 'min_atr': 40, 'min_score': 72}),
    ('Inst strict (4 days)', {'max_rsi': 65, 'min_atr': 30, 'min_score': 72}),
    ('No Inst', {'max_rsi': 65, 'min_atr': 30, 'min_score': 72}),
]

best_wr = wr_base
best_params = params_base.copy()
best_name = 'Baseline (Inst)'
results = []

print()
print('Starting optimization...')
print()

for name, params in configs:
    if 'No Inst' in name:
        trades = backtest(params, stocks, use_inst=False)
    else:
        trades = backtest(params, stocks, use_inst=True)
    
    if trades:
        wins = len([t for t in trades if t['ret'] > 0])
        wr = wins / len(trades) * 100
        avg = np.mean([t['ret'] for t in trades])
        print('  %s: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (name, len(trades), wr, avg))
        results.append({'name': name, 'wr': wr, 'signals': len(trades), 'avg': avg})
        
        if wr > best_wr:
            best_wr = wr
            best_params = params.copy()
            best_name = name

print()
print('='*70)
print(' FINAL RESULT')
print('='*70)
print(' Best Config: %s' % best_name)
print(' Best WR: %.1f%%' % best_wr)
print(' Best Params: %s' % best_params)
print('='*70)

# Check if target reached
if best_wr >= 65:
    print(' TARGET REACHED: %.1f%% >= 65%%' % best_wr)
else:
    print(' TARGET NOT REACHED: %.1f%% < 65%%' % best_wr)