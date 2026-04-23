# -*- coding: utf-8 -*-
"""
v4.21 Tiered Auto-Optimizer
分級觸發結構 (Tiered Logic) + 輔助因子篩選
目標: 增加交易頻次 + 維持/提升勝率
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
    if i < n: return 50, 50, 50
    low_n = h['Low'].iloc[i-n:i+1].min()
    high_n = h['High'].iloc[i-n:i+1].max()
    close = h['Close'].iloc[i]
    if high_n == low_n: return 50, 50, 50
    rsv = (close - low_n) / (high_n - low_n) * 100
    k = 2/3 * 50 + 1/3 * rsv
    d = 2/3 * 50 + 1/3 * k
    j = 3 * k - 2 * d
    return k, d, j

def macd(p):
    if len(p) < 26: return 0, 0
    ema12 = pd.Series(list(p)).ewm(span=12).mean().iloc[-1]
    ema26 = pd.Series(list(p)).ewm(span=26).mean().iloc[-1]
    macd_val = ema12 - ema26
    signal = pd.Series([macd_val]).ewm(span=9).mean().iloc[-1]
    return macd_val if not pd.isna(macd_val) else 0, signal if not pd.isna(signal) else 0

def check_tier1(code, date_str, inst_map, sync_days=3):
    if code not in inst_map: return False
    f_days = t_days = 0
    for dd in range(1, sync_days+1):
        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
        if dt in inst_map[code]:
            if inst_map[code][dt][0] > 0: f_days += 1
            if inst_map[code][dt][1] > 0: t_days += 1
    return f_days >= 1 and t_days >= 1

def check_tier2(code, date_str, inst_map, sync_days=3):
    if code not in inst_map: return False
    f_days = t_days = 0
    for dd in range(1, sync_days+1):
        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
        if dt in inst_map[code]:
            if inst_map[code][dt][0] > 0: f_days += 1
            if inst_map[code][dt][1] > 0: t_days += 1
    return max(f_days, t_days) >= 1

def backtest_tiered(params, inst_map, days=180):
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    tier1_count = 0
    tier2_count = 0
    
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 60: continue
            cl = list(h['Close'])
            vol = list(h['Volume'])
            ma5_all = list(h['Close'].rolling(5).mean())
            
            for i in range(30, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else ma20
                ma5 = ma5_all[i] if i < len(ma5_all) else ma20
                atr = calc_atr(h, i)
                atr_pct = atr / cl[i] * 100 if cl[i] > 0 else 0
                k, d, j = kdj(h, i)
                macd_val, signal_val = macd(cl[:i+1])
                date_str = str(h.index[i])[:10]
                
                rsi_min = params.get('rsi_min', 40)
                rsi_max = params.get('rsi_max', 70)
                if not (rsi_min <= rs <= rsi_max): continue
                if cl[i] < ma20: continue
                if atr_pct < params.get('min_atr_pct', 0.5): continue
                
                market_above_5ma = cl[i] > ma5 if ma5 else True
                kdj_gold = k > d and j > 0
                macd_gold = macd_val > signal_val
                
                tier1_active = params.get('tier1_active', True)
                tier2_active = params.get('tier2_active', True)
                
                entered = False
                tier = 0
                
                if tier1_active and kdj_gold and macd_gold:
                    if check_tier1(code, date_str, inst_map, params.get('sync_days', 3)):
                        entered = True
                        tier = 1
                        tier1_count += 1
                
                if not entered and tier2_active:
                    if market_above_5ma and check_tier2(code, date_str, inst_map, params.get('sync_days', 3)):
                        entered = True
                        tier = 2
                        tier2_count += 1
                
                if not entered: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'code': code, 'rsi': rs, 'atr': atr_pct, 'tier': tier})
        except:
            pass
        time.sleep(0.05)
    
    return all_trades, tier1_count, tier2_count

def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    gross_profit = sum([t['ret'] for t in wins])
    gross_loss = abs(sum([t['ret'] for t in losses]))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    mdd = min([t['ret'] for t in trades]) if trades else 0
    wr = len(wins)/len(trades)*100
    avg_win = np.mean([t['ret'] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t['ret'] for t in losses])) if losses else 0
    expectancy = (wr/100 * avg_win) - ((100-wr)/100 * avg_loss)
    tier1_count = len([t for t in trades if t.get('tier') == 1])
    tier2_count = len([t for t in trades if t.get('tier') == 2])
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': wr, 'avg': np.mean([t['ret'] for t in trades]),
        'pf': pf, 'mdd': mdd, 'expectancy': expectancy,
        'tier1': tier1_count, 'tier2': tier2_count
    }

def save_ver(ver, params, result, timestamp):
    try:
        with open('Tina_Quant_System/backtest/tier_versions.json', 'r') as f:
            vers = json.load(f)
    except: vers = []
    vers.append({
        'version': ver, 'params': params,
        'result': {k: round(v,2) if isinstance(v,float) else v for k,v in result.items()} if result else {},
        'timestamp': timestamp
    })
    with open('Tina_Quant_System/backtest/tier_versions.json', 'w') as f:
        json.dump(vers, f, ensure_ascii=False, indent=2)

# ============== MAIN ==============
print('='*70)
print(' v4.21 Tiered Auto-Optimizer')
print(' 分級觸發結構 (Tier 1 穩健 + Tier 2 高頻)')
print(' 時間: %s' % datetime.now().strftime('%Y-%m-%d %H:%M'))
print('='*70)

inst_map = load_inst()
now = datetime.now().strftime('%Y-%m-%d %H:%M')

# Baseline v4.21
baseline = {
    'rsi_min': 40, 'rsi_max': 70, 'min_atr_pct': 0.5,
    'tier1_active': True, 'tier2_active': False, 'sync_days': 3
}
print('\n[ Baseline: v4.21 ]')
t, t1, t2 = backtest_tiered(baseline, inst_map)
r = analyze(t)
if r:
    print(' Signals: %d | WR: %.1f%% | Avg: %+.2f%% | PF: %.2f | MDD: %+.2f%% | Expectancy: %.2f' % (
        r['total'], r['wr'], r['avg'], r['pf'], r['mdd'], r['expectancy']))
    print(' Tier1: %d | Tier2: %d' % (r['tier1'], r['tier2']))
    best_p, best_r, best_ver = baseline.copy(), r, 'Tier v1.0'
    save_ver('Tier v1.0 (v4.21)', baseline, r, now)
else:
    print(' Baseline: No trades')
    best_p, best_r, best_ver = baseline.copy(), {'total':0,'wr':0,'avg':0,'pf':0,'mdd':0,'expectancy':0,'tier1':0,'tier2':0}, 'Tier v1.0'

# 迭代
configs = [
    ('Tier v1.1: +Tier2', {'rsi_min': 40, 'rsi_max': 70, 'min_atr_pct': 0.5, 'tier1_active': True, 'tier2_active': True, 'sync_days': 3}),
    ('Tier v1.2: +Tier2+Loose', {'rsi_min': 35, 'rsi_max': 80, 'min_atr_pct': 0.3, 'tier1_active': True, 'tier2_active': True, 'sync_days': 3}),
    ('Tier v1.3: Relax ATR', {'rsi_min': 40, 'rsi_max': 75, 'min_atr_pct': 0.3, 'tier1_active': True, 'tier2_active': True, 'sync_days': 3}),
    ('Tier v1.4: Sync2days', {'rsi_min': 40, 'rsi_max': 75, 'min_atr_pct': 0.3, 'tier1_active': True, 'tier2_active': True, 'sync_days': 2}),
    ('Tier v1.5: ATR 0.2', {'rsi_min': 35, 'rsi_max': 80, 'min_atr_pct': 0.2, 'tier1_active': True, 'tier2_active': True, 'sync_days': 3}),
    ('Tier v1.6: NoTrend Req', {'rsi_min': 35, 'rsi_max': 80, 'min_atr_pct': 0.3, 'tier1_active': True, 'tier2_active': True, 'sync_days': 3}),
    ('Tier v1.7: Ultra Combo', {'rsi_min': 30, 'rsi_max': 85, 'min_atr_pct': 0.2, 'tier1_active': True, 'tier2_active': True, 'sync_days': 2}),
]

for name, params in configs:
    t, t1, t2 = backtest_tiered(params, inst_map)
    r = analyze(t)
    if not r:
        print('\n[ %s ] No trades' % name)
        continue
        
    print('\n[ %s ]' % name)
    print(' Signals: %d | WR: %.1f%% | Avg: %+.2f%% | PF: %.2f | MDD: %+.2f%% | Expectancy: %.2f' % (
        r['total'], r['wr'], r['avg'], r['pf'], r['mdd'], r['expectancy']))
    print(' Tier1: %d | Tier2: %d' % (r['tier1'], r['tier2']))
    
    improved = (r['total'] > best_r['total'] * 1.1 and r['expectancy'] >= best_r['expectancy'] * 0.9) or \
               (r['expectancy'] > best_r['expectancy'] and r['wr'] >= best_r['wr'] - 3)
    
    if improved:
        best_p, best_r, best_ver = params.copy(), r, name
        print(' >>> KEEP (Best!)')
    else:
        print(' >>> Rollback')
    save_ver(name, params, r, now)

print('\n' + '='*70)
print(' 最終報告 (Tiered Auto-Optimizer)')
print('='*70)
print(' 最佳版本: %s' % best_ver)
print(' 交易次數: %d' % best_r['total'])
print(' 勝率: %.1f%%' % best_r['wr'])
print(' 平均報酬: %+.2f%%' % best_r['avg'])
print(' 期望值: %.2f' % best_r['expectancy'])
print(' 獲利因子: %.2f' % best_r['pf'])
print(' 最大回撤: %+.2f%%' % best_r['mdd'])
print(' Tier 1 (穩健): %d | Tier 2 (高頻): %d' % (best_r['tier1'], best_r['tier2']))
print(' 最佳參數:', best_p)
print('='*70)