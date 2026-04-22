# -*- coding: utf-8 -*-
"""
市值前100大個股 - 交易策略自動化迭代優化系統
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

# ============== 股票池 ==============
STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428',
    '2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

BLACKLIST = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:100]

# ============== 載入法人資料 ==============
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

# ============== 技術指標 ==============
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

def macd_signal(p, fast=12, slow=26, signal=9):
    ema_fast = pd.Series(p).ewm(span=fast).mean()
    ema_slow = pd.Series(p).ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal).mean()
    return macd.iloc[-1] - signal_line.iloc[-1]

def kdj_signal(h, i, n=9):
    low_n = h['Low'].iloc[max(0,i-n):i+1].min()
    high_n = h['High'].iloc[max(0,i-n):i+1].max()
    close = h['Close'].iloc[i]
    rsv = (close - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
    k = 50
    d = 50
    j = 3 * k - 2 * d
    return k, d, j

# ============== 回測引擎 ==============
def backtest(params, inst_map, start='2026-01-01', end='2026-03-31'):
    all_trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 26: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)-1):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                atr_pct = calc_atr_pct(h, i)
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                macd_diff = macd_signal(cl[:i+1])
                k, d, j = kdj_signal(h, i)
                bias = (cl[i] / ma20 - 1) * 100
                date_str = str(h.index[i])[:10]
                
                # Filter: RSI
                if rs >= params.get('max_rsi', 70): continue
                # Filter: MA20
                if cl[i] < ma20: continue
                # Filter: ATR
                if atr_pct < params.get('min_atr', 0.5): continue
                # Filter: MACD
                if params.get('macd_pos', False) and macd_diff <= 0: continue
                # Filter: KDJ
                if params.get('kdj_buy', False) and (k < 20 or j < 0): continue
                
                # Institutional filter
                inst_days = params.get('inst_days', 0)
                if inst_days > 0 and code in inst_map:
                    f_days, t_days = 0, 0
                    for dd in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                elif inst_days > 0:
                    continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_idx = min(i+6, len(cl)-1)
                exit_p = cl[exit_idx]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                all_trades.append({
                    'ret': ret, 'rsi': rs, 'atr': atr_pct, 'vr': vr,
                    'macd': macd_diff, 'kdj_k': k, 'bias': bias, 'code': code
                })
        except:
            pass
        time.sleep(0.05)
    return all_trades

# ============== 分析引擎 ==============
def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    
    # Failure attribution
    fail_attrs = {
        'high_rsi': len([t for t in losses if t['rsi'] >= 65]),
        'low_atr': len([t for t in losses if t['atr'] < 1.0]),
        'low_vr': len([t for t in losses if t['vr'] < 1.0]),
        'macd_neg': len([t for t in losses if t['macd'] <= 0]),
        'kdj_overbought': len([t for t in losses if t['kdj_k'] > 80]),
    }
    
    return {
        'total': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'wr': len(wins) / len(trades) * 100,
        'avg_ret': np.mean([t['ret'] for t in trades]),
        'max_loss': min([t['ret'] for t in trades]),
        'fail_attrs': fail_attrs
    }

# ============== 版本控制 ==============
VERSION_FILE = 'Tina_Quant_System/backtest/optimizer_versions.json'

def save_version(version, params, result):
    try:
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            versions = json.load(f)
    except:
        versions = []
    
    versions.append({
        'version': version,
        'params': params,
        'result': result,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)

# ============== 主程式 ==============
print('='*70)
print(' 市值前100大個股 - 自動化策略迭代優化系統')
print('='*70)

inst_map = load_inst()

# 初始版本 (v1.0)
baseline = {
    'max_rsi': 70,
    'min_atr': 0.5,
    'inst_days': 3,
    'macd_pos': False,
    'kdj_buy': False
}

print('\n[Iteration 1: Baseline]')
print('參數:', baseline)
trades = backtest(baseline, inst_map)
result = analyze(trades)
print('結果: Signals=%d, WR=%.1f%%, Avg=%+.2f%%' % (result['total'], result['wr'], result['avg_ret']))
print('失敗分析:', result['fail_attrs'])

best_params = baseline.copy()
best_result = result
best_version = 1

save_version(1, baseline, result)

# Iteration 2: Add MACD filter
print('\n[Iteration 2: + MACD Filter]')
p2 = baseline.copy()
p2['macd_pos'] = True
trades = backtest(p2, inst_map)
result = analyze(trades)
print('參數:', p2)
print('結果: Signals=%d, WR=%.1f%%, Avg=%+.2f%%' % (result['total'], result['wr'], result['avg_ret']))

if result['wr'] >= best_result['wr']:
    best_params = p2.copy()
    best_result = result
    best_version = 2
    print('>>> WR提升，保留此版本')
else:
    print('>>> WR下降，Rollback')
save_version(2, p2, result)

# Iteration 3: Add KDJ filter
print('\n[Iteration 3: + KDJ Filter]')
p3 = best_params.copy()
p3['kdj_buy'] = True
trades = backtest(p3, inst_map)
result = analyze(trades)
print('參數:', p3)
print('結果: Signals=%d, WR=%.1f%%, Avg=%+.2f%%' % (result['total'], result['wr'], result['avg_ret']))

if result['wr'] >= best_result['wr']:
    best_params = p3.copy()
    best_result = result
    best_version = 3
    print('>>> WR提升，保留此版本')
else:
    print('>>> WR下降，Rollback')
save_version(3, p3, result)

# Iteration 4: Relax RSI
print('\n[Iteration 4: Relax RSI to 75]')
p4 = best_params.copy()
p4['max_rsi'] = 75
trades = backtest(p4, inst_map)
result = analyze(trades)
print('參數:', p4)
print('結果: Signals=%d, WR=%.1f%%, Avg=%+.2f%%' % (result['total'], result['wr'], result['avg_ret']))

if result['wr'] >= best_result['wr'] and result['total'] > best_result['total']:
    best_params = p4.copy()
    best_result = result
    best_version = 4
    print('>>> WR或Signals提升，保留此版本')
else:
    print('>>> 績效下降，Rollback')
save_version(4, p4, result)

# Final Report
print('\n' + '='*70)
print(' 最终报告')
print('='*70)
print('最佳版本: v%d' % best_version)
print('最佳參數:', best_params)
print('最佳結果: Signals=%d, WR=%.1f%%, Avg=%+.2f%%' % (best_result['total'], best_result['wr'], best_result['avg_ret']))
print('失敗分析:', best_result['fail_attrs'])
print('='*70)