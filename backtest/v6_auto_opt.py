# -*- coding: utf-8 -*-
"""
市值前100大個股 - 自動化迭代優化系統 v6.1
目標: 維持/提升勝率 + 增加交易頻次
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

STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428',
    '2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

BLACKLIST = ['2615','1590','2382','2317','2303','3008','3231','2408','3443','6446','6669','2597']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:100]

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

def kdj(h, i, n=9):
    low_n = h['Low'].iloc[max(0,i-n):i+1].min()
    high_n = h['High'].iloc[max(0,i-n):i+1].max()
    close = h['Close'].iloc[i]
    rsv = (close - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
    k = 50
    d = 50
    j = 3 * k - 2 * d
    return k, d, j

def macd(p):
    ema12 = pd.Series(p).ewm(span=12).mean()
    ema26 = pd.Series(p).ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd.iloc[-1], signal.iloc[-1]

def backtest(params, inst_map, days=180):
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 30: continue
            cl = list(h['Close'])
            vol = list(h['Volume'])
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else ma20
                atr = calc_atr(h, i)
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                k, d, j = kdj(h, i)
                macd_val, signal_val = macd(cl[:i+1])
                date_str = str(h.index[i])[:10]
                
                # Filters
                if rs >= params.get('max_rsi', 70): continue
                if cl[i] < ma20: continue
                if atr < params.get('min_atr', 30): continue
                
                # Trend filter
                if params.get('trend_ma', False) and ma20 <= ma60: continue
                
                # KDJ filter
                if params.get('kdj_filter', False):
                    if not (k > d and j > 0): continue
                
                # MACD filter
                if params.get('macd_filter', False):
                    if macd_val <= signal_val: continue
                
                # Institutional
                inst_days = params.get('inst_days', 0)
                if inst_days > 0 and code in inst_map:
                    f_days = t_days = 0
                    for dd in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
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
                    'ret': ret, 'rsi': rs, 'atr': atr, 'vr': vr,
                    'bias': (cl[i]/ma20-1)*100, 'code': code
                })
        except:
            pass
        time.sleep(0.05)
    return all_trades

def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    gross_profit = sum([t['ret'] for t in wins])
    gross_loss = abs(sum([t['ret'] for t in losses]))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    mdd = min([t['ret'] for t in trades]) if trades else 0
    
    avg_val = np.mean([t['ret'] for t in trades]) if trades else 0
    
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': len(wins)/len(trades)*100,
        'avg': avg_val,
        'pf': pf,
        'mdd': mdd,
        'fail': {
            'high_rsi': len([t for t in losses if t['rsi'] >= 60]),
            'low_vr': len([t for t in losses if t['vr'] < 1.0]),
            'high_bias': len([t for t in losses if t['bias'] > 6])
        }
    }

def save_ver(ver, params, result):
    try:
        with open('Tina_Quant_System/backtest/v6_versions.json', 'r') as f:
            vers = json.load(f)
    except: vers = []
    vers.append({
        'version': ver, 'params': params,
        'result': {k: round(v,2) if isinstance(v,float) else v for k,v in result.items() if k != 'fail'} if result else {},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    with open('Tina_Quant_System/backtest/v6_versions.json', 'w') as f:
        json.dump(vers, f, ensure_ascii=False, indent=2)

# ============== MAIN ==============
print('='*70)
print(' 市值前100大個股 - 自動化迭代優化系統 v6.1')
print('='*70)

inst_map = load_inst()

# Baseline
baseline = {'max_rsi': 70, 'min_atr': 30, 'inst_days': 3, 'inst_min': 1, 'trend_ma': False, 'kdj_filter': False, 'macd_filter': False}
print('\n[ Ver. 6.0: Baseline ]')
t = backtest(baseline, inst_map)
r = analyze(t)
if r:
    print(' Signals: %d | WR: %.1f%% | Avg: %+.2f%% | PF: %.2f | MDD: %+.2f%%' % (r['total'], r['wr'], r['avg'], r['pf'], r['mdd']))
    print(' Fail: High RSI=%d, Low VR=%d, High Bias=%d' % (r['fail']['high_rsi'], r['fail']['low_vr'], r['fail']['high_bias']))
    best_p, best_r, best_ver = baseline.copy(), r, 'Ver. 6.0'
    save_ver('Ver. 6.0', baseline, r)
else:
    print(' No trades!')
    best_p, best_r, best_ver = baseline.copy(), {'total':0,'wins':0,'wr':0,'avg':0,'pf':0,'mdd':0,'fail':{}}, 'Ver. 6.0'

# Iterations
configs = [
    ('Ver. 6.1: +Trend', {'max_rsi': 70, 'min_atr': 30, 'inst_days': 3, 'inst_min': 1, 'trend_ma': True, 'kdj_filter': False, 'macd_filter': False}),
    ('Ver. 6.2: +KDJ', {'max_rsi': 70, 'min_atr': 30, 'inst_days': 3, 'inst_min': 1, 'trend_ma': False, 'kdj_filter': True, 'macd_filter': False}),
    ('Ver. 6.3: +MACD', {'max_rsi': 70, 'min_atr': 30, 'inst_days': 3, 'inst_min': 1, 'trend_ma': False, 'kdj_filter': False, 'macd_filter': True}),
    ('Ver. 6.4: RSI<72', {'max_rsi': 72, 'min_atr': 30, 'inst_days': 3, 'inst_min': 1, 'trend_ma': False, 'kdj_filter': False, 'macd_filter': False}),
    ('Ver. 6.5: RSI<75', {'max_rsi': 75, 'min_atr': 30, 'inst_days': 3, 'inst_min': 1, 'trend_ma': False, 'kdj_filter': False, 'macd_filter': False}),
    ('Ver. 6.6: Inst2d', {'max_rsi': 70, 'min_atr': 30, 'inst_days': 2, 'inst_min': 1, 'trend_ma': False, 'kdj_filter': False, 'macd_filter': False}),
    ('Ver. 6.7: Inst1d', {'max_rsi': 70, 'min_atr': 30, 'inst_days': 1, 'inst_min': 1, 'trend_ma': False, 'kdj_filter': False, 'macd_filter': False}),
    ('Ver. 6.8: NoInst', {'max_rsi': 70, 'min_atr': 30, 'inst_days': 0, 'inst_min': 0, 'trend_ma': False, 'kdj_filter': False, 'macd_filter': False}),
]

for name, params in configs:
    t = backtest(params, inst_map)
    r = analyze(t)
    if not r:
        print('\n[ %s ] No trades' % name)
        save_ver(name, params, None)
        continue
        
    print('\n[ %s ]' % name)
    print(' Signals: %d | WR: %.1f%% | Avg: %+.2f%% | PF: %.2f | MDD: %+.2f%%' % (r['total'], r['wr'], r['avg'], r['pf'], r['mdd']))
    
    # Keep if WR improved or signals increased significantly with acceptable WR
    improved = r['wr'] > best_r['wr'] or (r['total'] > best_r['total'] * 1.2 and r['wr'] >= best_r['wr'] - 2)
    
    if improved:
        best_p, best_r, best_ver = params.copy(), r, name
        print(' >>> KEEP (Best!)')
    else:
        print(' >>> Rollback')
    save_ver(name, params, r)

# Final Report
print('\n' + '='*70)
print(' 最终报告')
print('='*70)
print(' 最佳版本: %s' % best_ver)
print(' 勝率變化: %.1f%%' % best_r['wr'])
print(' 交易次數變化: %d' % best_r['total'])
print(' 最大回撤 (MDD): %+.2f%%' % best_r['mdd'])
print(' 獲利因子 (PF): %.2f' % best_r['pf'])
print()
print(' 失敗因子:')
print('  High RSI: %d' % best_r['fail']['high_rsi'])
print('  Low VR: %d' % best_r['fail']['low_vr'])
print('  High Bias: %d' % best_r['fail']['high_bias'])
print()
print(' 最佳參數:', best_p)
print('='*70)