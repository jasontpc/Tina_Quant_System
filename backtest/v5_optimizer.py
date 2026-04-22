# -*- coding: utf-8 -*-
"""
市值前200大個股 - v5 自動化策略迭代優化系統
分層過濾 + 組合式邏輯 + 動態VIF
目標: 突破45%勝率瓶頸，達到55-60%
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

# ============== 股票池分層 ==============
TOP50 = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428']

TOP51_200 = ['2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

BLACKLIST = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
TOP50 = [s for s in TOP50 if s not in BLACKLIST]
TOP51_200 = [s for s in TOP51_200 if s not in BLACKLIST]
ALL_STOCKS = TOP50 + TOP51_200

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
    return (atr / close[-1]) * 100, atr

def macd_signal(p):
    ema12 = pd.Series(p).ewm(span=12).mean()
    ema26 = pd.Series(p).ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd.iloc[-1], signal.iloc[-1]

def get_ma200(cl):
    if len(cl) < 200: return 0
    return np.mean(cl[-200:])

# ============== 分層回測引擎 ==============
def backtest_v5(params, inst_map, start='2026-01-01', end='2026-03-31'):
    """
    分層過濾:
    - Top50: 標準技術指標
    - Top51-200: 嚴格法人籌碼 + 動態VIF
    """
    all_trades = {'top50': [], 'top51_200': [], 'all': []}
    avg_atr = 0
    atr_count = 0
    
    for code in ALL_STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 60: continue  # Need MA200 data
            cl, vol = list(h['Close']), list(h['Volume'])
            
            # Calculate average ATR for dynamic VIF
            for i in range(25, len(cl)-6):
                atr_pct, atr_val = calc_atr_pct(h, i)
                avg_atr += atr_pct
                atr_count += 1
            avg_atr_pct = avg_atr / atr_count if atr_count > 0 else 0.5
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma200 = get_ma200(cl[:i+1])
                atr_pct, atr_val = calc_atr_pct(h, i)
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                macd_val, signal_val = macd_signal(cl[:i+1])
                bias = (cl[i] / ma20 - 1) * 100
                date_str = str(h.index[i])[:10]
                
                # === 動態VIF門檻 ===
                dynamic_vif_min = 1.5 if atr_pct < avg_atr_pct else params.get('min_vif', 1.0)
                
                # === Top50 分層邏輯 ===
                if code in TOP50:
                    # 權值股: 標準過濾
                    if rs >= params.get('max_rsi', 70): continue
                    if cl[i] < ma20: continue
                    if atr_pct < params.get('min_atr', 0.5): continue
                    if vr < dynamic_vif_min: continue
                    
                    # 多頭模式 (Price > MA200)
                    if cl[i] > ma200 and ma200 > 0:
                        if params.get('macd_bull', False):
                            if macd_val <= signal_val: continue
                    # 空頭模式 (Price < MA200)
                    elif cl[i] < ma200 and ma200 > 0:
                        if params.get('conservative_mode', True):
                            if rs >= params.get('max_rsi', 65) - 5: continue
                            if vr < dynamic_vif_min + 0.3: continue
                
                # === Top51-200 分層邏輯 ===
                else:
                    # 嚴格法人籌碼
                    inst_days = params.get('inst_days', 3)
                    if code in inst_map:
                        f_days, t_days = 0, 0
                        for d in range(1, inst_days+1):
                            dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                            if dt in inst_map[code]:
                                f_net, t_net = inst_map[code][dt]
                                if f_net > 0: f_days += 1
                                if t_net > 0: t_days += 1
                        # 強制: 連續3日法人買超
                        if f_days < 3 and t_days < 3: continue
                    else:
                        continue  # 無法人資料就跳過
                    
                    # 技術指標
                    if rs >= params.get('max_rsi', 68): continue
                    if cl[i] < ma20: continue
                    if atr_pct < params.get('min_atr', 0.5): continue
                    if vr < dynamic_vif_min: continue
                
                # 進場
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                trade = {'ret': ret, 'rsi': rs, 'atr': atr_pct, 'vr': vr, 
                         'macd': macd_val - signal_val, 'bias': bias, 'code': code}
                
                if code in TOP50:
                    all_trades['top50'].append(trade)
                else:
                    all_trades['top51_200'].append(trade)
                all_trades['all'].append(trade)
                    
        except:
            pass
        time.sleep(0.05)
    
    return all_trades

# ============== 分析引擎 ==============
def analyze_v5(trades):
    results = {}
    for key in ['top50', 'top51_200', 'all']:
        t = trades[key]
        if not t:
            results[key] = {'signals': 0, 'wr': 0, 'avg': 0, 'wins': 0}
            continue
        wins = len([x for x in t if x['ret'] > 0])
        losses = [x for x in t if x['ret'] <= 0]
        
        # Failure attribution
        fail_high_rsi = len([x for x in losses if x['rsi'] >= 65])
        fail_low_vr = len([x for x in losses if x['vr'] < 1.0])
        fail_neg_macd = len([x for x in losses if x['macd'] <= 0])
        
        results[key] = {
            'signals': len(t),
            'wins': wins,
            'wr': wins / len(t) * 100,
            'avg': np.mean([x['ret'] for x in t]),
            'fail_attrs': {
                'high_rsi': fail_high_rsi,
                'low_vr': fail_low_vr,
                'neg_macd': fail_neg_macd
            }
        }
    return results

# ============== 版本控制 ==============
def save_version(ver, params, results):
    try:
        with open('Tina_Quant_System/backtest/v5_versions.json', 'r', encoding='utf-8') as f:
            versions = json.load(f)
    except:
        versions = []
    
    versions.append({
        'version': ver,
        'params': params,
        'results': results,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    
    with open('Tina_Quant_System/backtest/v5_versions.json', 'w', encoding='utf-8') as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)

# ============== 主程式 ==============
print('='*70)
print(' v5 自動化策略迭代優化系統')
print(' 分層過濾 + 組合式邏輯 + 動態VIF')
print('='*70)

inst_map = load_inst()

# v5.0: Baseline with layered filtering
print('\n[ v5.0: Baseline 分層過濾 ]')
p0 = {
    'max_rsi': 70,
    'min_atr': 0.5,
    'min_vif': 1.0,
    'inst_days': 3,
    'macd_bull': False,
    'conservative_mode': True
}
trades = backtest_v5(p0, inst_map)
r0 = analyze_v5(trades)
print(' Top50: Signals=%d, WR=%.1f%%' % (r0['top50']['signals'], r0['top50']['wr']))
print(' Top51-200: Signals=%d, WR=%.1f%%' % (r0['top51_200']['signals'], r0['top51_200']['wr']))
print(' Overall: Signals=%d, WR=%.1f%%' % (r0['all']['signals'], r0['all']['wr']))

best_params = p0.copy()
best_results = r0.copy()
best_ver = 'v5.0'
save_version('v5.0', p0, r0)

# v5.1: Relax RSI for Top50
print('\n[ v5.1: Top50 RSI放寬至75 ]')
p1 = best_params.copy()
p1['max_rsi'] = 75
trades = backtest_v5(p1, inst_map)
r1 = analyze_v5(trades)
print(' Top50: Signals=%d, WR=%.1f%%' % (r1['top50']['signals'], r1['top50']['wr']))
print(' Top51-200: Signals=%d, WR=%.1f%%' % (r1['top51_200']['signals'], r1['top51_200']['wr']))
print(' Overall: Signals=%d, WR=%.1f%%' % (r1['all']['signals'], r1['all']['wr']))

if r1['all']['wr'] >= best_results['all']['wr']:
    best_params = p1.copy()
    best_results = r1.copy()
    best_ver = 'v5.1'
    print('>>> 勝率提升，保留')
else:
    print('>>> 勝率下降，Rollback')
save_version('v5.1', p1, r1)

# v5.2: Enable MACD Bull Mode
print('\n[ v5.2: 啟用MACD多頭濾網 ]')
p2 = best_params.copy()
p2['macd_bull'] = True
trades = backtest_v5(p2, inst_map)
r2 = analyze_v5(trades)
print(' Top50: Signals=%d, WR=%.1f%%' % (r2['top50']['signals'], r2['top50']['wr']))
print(' Top51-200: Signals=%d, WR=%.1f%%' % (r2['top51_200']['signals'], r2['top51_200']['wr']))
print(' Overall: Signals=%d, WR=%.1f%%' % (r2['all']['signals'], r2['all']['wr']))

if r2['all']['wr'] >= best_results['all']['wr']:
    best_params = p2.copy()
    best_results = r2.copy()
    best_ver = 'v5.2'
    print('>>> 勝率提升，保留')
else:
    print('>>> 勝率下降，Rollback')
save_version('v5.2', p2, r2)

# v5.3: Dynamic VIF with ATR condition
print('\n[ v5.3: 動態VIF (ATR低時VIF提高至1.5) ]')
p3 = best_params.copy()
p3['min_vif'] = 1.5  # Higher VIF when ATR is low
trades = backtest_v5(p3, inst_map)
r3 = analyze_v5(trades)
print(' Top50: Signals=%d, WR=%.1f%%' % (r3['top50']['signals'], r3['top50']['wr']))
print(' Top51-200: Signals=%d, WR=%.1f%%' % (r3['top51_200']['signals'], r3['top51_200']['wr']))
print(' Overall: Signals=%d, WR=%.1f%%' % (r3['all']['signals'], r3['all']['wr']))

if r3['all']['wr'] >= best_results['all']['wr']:
    best_params = p3.copy()
    best_results = r3.copy()
    best_ver = 'v5.3'
    print('>>> 勝率提升，保留')
else:
    print('>>> 勝率下降，Rollback')
save_version('v5.3', p3, r3)

# v5.4: Combine best of v5.1 + v5.3
print('\n[ v5.4: RSI75 + DynamicVIF ]')
p4 = best_params.copy()
p4['max_rsi'] = 75
p4['min_vif'] = 1.3
trades = backtest_v5(p4, inst_map)
r4 = analyze_v5(trades)
print(' Top50: Signals=%d, WR=%.1f%%' % (r4['top50']['signals'], r4['top50']['wr']))
print(' Top51-200: Signals=%d, WR=%.1f%%' % (r4['top51_200']['signals'], r4['top51_200']['wr']))
print(' Overall: Signals=%d, WR=%.1f%%' % (r4['all']['signals'], r4['all']['wr']))

if r4['all']['wr'] >= best_results['all']['wr']:
    best_params = p4.copy()
    best_results = r4.copy()
    best_ver = 'v5.4'
    print('>>> 勝率提升，保留')
else:
    print('>>> 勝率下降，Rollback')
save_version('v5.4', p4, r4)

# Final Report
print('\n' + '='*70)
print(' v5 最終報告')
print('='*70)
print('最佳版本:', best_ver)
print()
print('分層表現:')
print('  Top 1-50:')
print('    Signals: %d' % best_results['top50']['signals'])
print('    WR: %.1f%%' % best_results['top50']['wr'])
print('    Avg Return: %+.2f%%' % best_results['top50']['avg'])
print()
print('  Top 51-200:')
print('    Signals: %d' % best_results['top51_200']['signals'])
print('    WR: %.1f%%' % best_results['top51_200']['wr'])
print('    Avg Return: %+.2f%%' % best_results['top51_200']['avg'])
print()
print('  Overall:')
print('    Signals: %d' % best_results['all']['signals'])
print('    WR: %.1f%%' % best_results['all']['wr'])
print('    Avg Return: %+.2f%%' % best_results['all']['avg'])
print()
print('失敗因子熱點圖:')
print('  High RSI: %d' % best_results['all']['fail_attrs']['high_rsi'])
print('  Low VIF: %d' % best_results['all']['fail_attrs']['low_vr'])
print('  Negative MACD: %d' % best_results['all']['fail_attrs']['neg_macd'])
print()
print('最佳參數:', best_params)
print('='*70)