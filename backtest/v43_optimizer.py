# -*- coding: utf-8 -*-
"""
市值前50大個股 - v4.3 自動化策略迭代優化系統
目標: 提升交易頻次 + 維持/提高勝率
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
import json
from datetime import datetime

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# ============== 股票池 Top50 ==============
STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402']

BLACKLIST = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:50]

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

def backtest(params, inst_map, start='2026-01-01', end='2026-03-31'):
    all_trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 26: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                atr_pct = calc_atr_pct(h, i)
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                date_str = str(h.index[i])[:10]
                
                # Filters
                if rs >= params.get('max_rsi', 70): continue
                if cl[i] < ma20: continue
                if atr_pct < params.get('min_atr', 0.5): continue
                if vr < params.get('min_vif', 0.5): continue
                
                # Institutional filter
                inst_days = params.get('inst_days', 0)
                if inst_days > 0 and code in inst_map:
                    f_days, t_days = 0, 0
                    for d in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < params.get('inst_min', 1): continue
                elif inst_days > 0:
                    continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                all_trades.append({
                    'ret': ret, 'rsi': rs, 'atr': atr_pct, 'vr': vr,
                    'bias': (cl[i] / ma20 - 1) * 100, 'code': code
                })
        except:
            pass
        time.sleep(0.05)
    return all_trades

def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': len(wins) / len(trades) * 100,
        'avg': np.mean([t['ret'] for t in trades]),
        'max_win': max([t['ret'] for t in trades]) if trades else 0,
        'max_loss': min([t['ret'] for t in trades]) if trades else 0,
        'fail': {
            'high_rsi': len([t for t in losses if t['rsi'] >= 65]),
            'low_vr': len([t for t in losses if t['vr'] < 1.0]),
            'high_bias': len([t for t in losses if t['bias'] > 5])
        }
    }

def save_ver(ver, params, result):
    try:
        with open('Tina_Quant_System/backtest/v43_versions.json', 'r') as f:
            vers = json.load(f)
    except: vers = []
    vers.append({'version': ver, 'params': params, 'result': {k:v for k,v in result.items() if k != 'fail'}, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')})
    with open('Tina_Quant_System/backtest/v43_versions.json', 'w') as f:
        json.dump(vers, f, ensure_ascii=False, indent=2)

# ============== 主程式 ==============
print('='*70)
print(' 市值前50大個股 - v4.3 自動化迭代優化')
print('='*70)

inst_map = load_inst()

# Baseline
p0 = {'max_rsi': 70, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 3, 'inst_min': 1}
t = backtest(p0, inst_map)
r = analyze(t)
print('\n[ v4.3.0: Baseline ]')
print(' Signals=%d, WR=%.1f%%, Avg=%+.2f%%' % (r['total'], r['wr'], r['avg']))
print(' Fail: High RSI=%d, Low VIF=%d, High Bias=%d' % (r['fail']['high_rsi'], r['fail']['low_vr'], r['fail']['high_bias']))
best_p, best_r, best_ver = p0.copy(), r, 'v4.3.0'
save_ver('v4.3.0', p0, r)

# Iterations
configs = [
    ('v4.3.1: RSI<72', {'max_rsi': 72, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 3, 'inst_min': 1}),
    ('v4.3.2: RSI<75', {'max_rsi': 75, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 3, 'inst_min': 1}),
    ('v4.3.3: Inst 2d', {'max_rsi': 70, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 2, 'inst_min': 1}),
    ('v4.3.4: Inst 1d', {'max_rsi': 70, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 1, 'inst_min': 1}),
    ('v4.3.5: No Inst', {'max_rsi': 70, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 0, 'inst_min': 0}),
    ('v4.3.6: RSI75+Inst1d', {'max_rsi': 75, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 1, 'inst_min': 1}),
    ('v4.3.7: RSI78', {'max_rsi': 78, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 3, 'inst_min': 1}),
    ('v4.3.8: RSI80', {'max_rsi': 80, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 3, 'inst_min': 1}),
    ('v4.3.9: ATR>=0.3', {'max_rsi': 70, 'min_atr': 0.3, 'min_vif': 0.5, 'inst_days': 3, 'inst_min': 1}),
    ('v4.3.10: RSI78+Inst1d', {'max_rsi': 78, 'min_atr': 0.5, 'min_vif': 0.5, 'inst_days': 1, 'inst_min': 1}),
]

for name, params in configs:
    t = backtest(params, inst_map)
    r = analyze(t)
    print('\n[ %s ]' % name)
    print(' Signals=%d, WR=%.1f%%, Avg=%+.2f%%' % (r['total'], r['wr'], r['avg']))
    
    # Keep if WR improved or signals significantly increased with acceptable WR
    if r['wr'] >= best_r['wr'] or (r['total'] > best_r['total'] * 1.2 and r['wr'] >= best_r['wr'] - 3):
        best_p, best_r, best_ver = params.copy(), r, name
        print(' >>> 保留 (Best!)')
    else:
        print(' >>> Rollback')
    save_ver(name, params, r)

# Final Report
print('\n' + '='*70)
print(' v4.3 最終報告')
print('='*70)
print(' 最佳版本:', best_ver)
print(' 總交易次數:', best_r['total'])
print(' 勝利:', best_r['wins'])
print(' 失敗:', best_r['losses'])
print(' 勝率: %.1f%%' % best_r['wr'])
print(' 平均報酬: %+.2f%%' % best_r['avg'])
print(' 最大獲利: %+.2f%%' % best_r['max_win'])
print(' 最大虧損: %+.2f%%' % best_r['max_loss'])
print()
print(' 失敗因子:')
print('  High RSI:', best_r['fail']['high_rsi'])
print('  Low VIF:', best_r['fail']['low_vr'])
print('  High Bias:', best_r['fail']['high_bias'])
print()
print(' 最佳參數:', best_p)
print('='*70)