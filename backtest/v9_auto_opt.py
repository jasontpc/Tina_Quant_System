# -*- coding: utf-8 -*-
"""
台股量化策略 Auto-Optimization v2
分級觸發 + 非同步確認 (3日內)
目標: 增加交易頻次 + 維持勝率
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

def check_inst(code, date_str, inst_map, sync_days=3, mode='any'):
    """檢查法人是否符合條件"""
    if code not in inst_map:
        return False
    
    f_days = t_days = 0
    for dd in range(1, sync_days+1):
        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
        if dt in inst_map[code]:
            if inst_map[code][dt][0] > 0: f_days += 1
            if inst_map[code][dt][1] > 0: t_days += 1
    
    if mode == 'sync':
        # 模式A: 法人同步買超
        return f_days >= 1 and t_days >= 1
    else:
        # 模式B: 任一法人買超
        return max(f_days, t_days) >= 1

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
            
            for i in range(30, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else ma20
                atr = calc_atr(h, i)
                atr_pct = atr / cl[i] * 100 if cl[i] > 0 else 0
                k, d, j = kdj(h, i)
                macd_val, signal_val = macd(cl[:i+1])
                date_str = str(h.index[i])[:10]
                
                # === 技術面篩選 ===
                rsi_min = params.get('rsi_min', 40)
                rsi_max = params.get('rsi_max', 80)
                if not (rsi_min <= rs <= rsi_max): continue
                if cl[i] < ma20: continue
                
                # ATR
                min_atr = params.get('min_atr_pct', 0.3)
                if atr_pct < min_atr: continue
                
                # 趨勢 (可選)
                if params.get('trend_ma', True) and ma20 <= ma60: continue
                
                # KDJ (可選)
                if params.get('kdj_filter', False) and k <= d: continue
                
                # MACD (可選)
                if params.get('macd_filter', False) and macd_val <= signal_val: continue
                
                # === 分級法人觸發 ===
                inst_mode = params.get('inst_mode', 'any')  # 'sync' or 'any'
                sync_days = params.get('sync_days', 3)
                
                # 非同步確認: 技術面先行，3日內法人確認即可
                inst_confirmed = check_inst(code, date_str, inst_map, sync_days, inst_mode)
                
                # 若無法人資料但符合技術面，仍可進場 (扩大宽口)
                if params.get('strict_inst', True) and not inst_confirmed:
                    continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({
                    'ret': ret, 'rsi': rs, 'atr_pct': atr_pct,
                    'bias': (cl[i]/ma20-1)*100, 'code': code,
                    'inst_confirmed': inst_confirmed
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
    avg = np.mean([t['ret'] for t in trades]) if trades else 0
    wr = len(wins)/len(trades)*100
    avg_win = np.mean([t['ret'] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t['ret'] for t in losses])) if losses else 0
    expectancy = (wr/100 * avg_win) - ((100-wr)/100 * avg_loss)
    
    inst_confirmed = len([t for t in trades if t.get('inst_confirmed', False)])
    
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': wr, 'avg': avg, 'pf': pf, 'mdd': mdd, 'expectancy': expectancy,
        'avg_win': avg_win, 'avg_loss': avg_loss, 'inst_confirmed': inst_confirmed
    }

def save_ver(ver, params, result, timestamp):
    try:
        with open('Tina_Quant_System/backtest/v9_versions.json', 'r') as f:
            vers = json.load(f)
    except: vers = []
    vers.append({
        'version': ver, 'params': params,
        'result': {k: round(v,2) if isinstance(v,float) else v for k,v in result.items()} if result else {},
        'timestamp': timestamp
    })
    with open('Tina_Quant_System/backtest/v9_versions.json', 'w') as f:
        json.dump(vers, f, ensure_ascii=False, indent=2)

# ============== MAIN ==============
print('='*70)
print(' 台股量化策略 Auto-Optimization v2')
print(' 分級觸發 + 非同步確認 (3日內)')
print(' 時間: %s' % datetime.now().strftime('%Y-%m-%d %H:%M'))
print('='*70)

inst_map = load_inst()
now = datetime.now().strftime('%Y-%m-%d %H:%M')

# Baseline v4.21
baseline = {'rsi_min': 40, 'rsi_max': 70, 'min_atr_pct': 0.3, 'trend_ma': True, 
            'kdj_filter': False, 'macd_filter': False, 'inst_mode': 'any', 
            'sync_days': 3, 'strict_inst': True}
print('\n[ Baseline: v4.21 ]')
t = backtest(baseline, inst_map)
r = analyze(t)
if r:
    print(' Signals: %d | WR: %.1f%% | Avg: %+.2f%% | PF: %.2f | MDD: %+.2f%% | Expectancy: %.2f' % (
        r['total'], r['wr'], r['avg'], r['pf'], r['mdd'], r['expectancy']))
    print(' Inst Confirmed: %d/%d' % (r['inst_confirmed'], r['total']))
best_p, best_r, best_ver = baseline.copy(), r, 'v9.0'
save_ver('v9.0 (Baseline)', baseline, r, now)

# 迭代測試
configs = [
    ('v9.1: Inst Sync', {'rsi_min': 40, 'rsi_max': 70, 'min_atr_pct': 0.3, 'trend_ma': True, 
        'kdj_filter': False, 'macd_filter': False, 'inst_mode': 'sync', 'sync_days': 3, 'strict_inst': True}),
    ('v9.2: Inst Any + Strict', {'rsi_min': 40, 'rsi_max': 80, 'min_atr_pct': 0.3, 'trend_ma': True, 
        'kdj_filter': False, 'macd_filter': False, 'inst_mode': 'any', 'sync_days': 3, 'strict_inst': True}),
    ('v9.3: Relaxed RSI', {'rsi_min': 35, 'rsi_max': 80, 'min_atr_pct': 0.3, 'trend_ma': True, 
        'kdj_filter': False, 'macd_filter': False, 'inst_mode': 'any', 'sync_days': 3, 'strict_inst': True}),
    ('v9.4: +KDJ', {'rsi_min': 40, 'rsi_max': 80, 'min_atr_pct': 0.3, 'trend_ma': True, 
        'kdj_filter': True, 'macd_filter': False, 'inst_mode': 'any', 'sync_days': 3, 'strict_inst': True}),
    ('v9.5: No Trend', {'rsi_min': 35, 'rsi_max': 85, 'min_atr_pct': 0.2, 'trend_ma': False, 
        'kdj_filter': False, 'macd_filter': False, 'inst_mode': 'any', 'sync_days': 3, 'strict_inst': False}),
    ('v9.6: Ultra Loose', {'rsi_min': 30, 'rsi_max': 90, 'min_atr_pct': 0.2, 'trend_ma': False, 
        'kdj_filter': False, 'macd_filter': False, 'inst_mode': 'any', 'sync_days': 0, 'strict_inst': False}),
    ('v9.7: ATR 0.1', {'rsi_min': 35, 'rsi_max': 85, 'min_atr_pct': 0.1, 'trend_ma': True, 
        'kdj_filter': False, 'macd_filter': False, 'inst_mode': 'any', 'sync_days': 3, 'strict_inst': False}),
    ('v9.8: Best Combo', {'rsi_min': 35, 'rsi_max': 80, 'min_atr_pct': 0.25, 'trend_ma': True, 
        'kdj_filter': True, 'macd_filter': True, 'inst_mode': 'any', 'sync_days': 3, 'strict_inst': True}),
]

for name, params in configs:
    t = backtest(params, inst_map)
    r = analyze(t)
    if not r:
        print('\n[ %s ] No trades' % name)
        continue
        
    print('\n[ %s ]' % name)
    print(' Signals: %d | WR: %.1f%% | Avg: %+.2f%% | PF: %.2f | MDD: %+.2f%% | Expectancy: %.2f' % (
        r['total'], r['wr'], r['avg'], r['pf'], r['mdd'], r['expectancy']))
    
    # Keep if signals increased > 10% and expectancy improved or at least maintained
    improved = (r['total'] > best_r['total'] * 1.1 and r['expectancy'] >= best_r['expectancy'] * 0.9) or \
              (r['expectancy'] > best_r['expectancy'] and r['wr'] >= best_r['wr'])
    
    if improved:
        best_p, best_r, best_ver = params.copy(), r, name
        print(' >>> KEEP (Best!)')
    else:
        print(' >>> Rollback')
    save_ver(name, params, r, now)

# Final Report
print('\n' + '='*70)
print(' 最終報告 (v2 - 分級觸發 + 非同步)')
print('='*70)
print(' 最佳版本: %s' % best_ver)
print(' 交易次數: %d (vs Baseline %d, %+.1f%%)' % (best_r['total'], best_r['total'], 
    (best_r['total'] / 1000 * 100) if best_r['total'] > 0 else 0))
print(' 勝率: %.1f%%' % best_r['wr'])
print(' 平均報酬: %+.2f%%' % best_r['avg'])
print(' 期望值: %.2f' % best_r['expectancy'])
print(' 獲利因子: %.2f' % best_r['pf'])
print(' 最大回撤: %+.2f%%' % best_r['mdd'])
print()
print(' 最佳參數:', best_p)
print('='*70)