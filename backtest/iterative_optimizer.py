# -*- coding: utf-8 -*-
"""
Tina v4.21 失敗分析與自動迭代優化系統
股票池: 台股市值前100大
回測區間: 滾動120日
自動分析失敗原因 -> 修正參數 -> 回測 -> 比較 -> Rollback/Accept
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import json
from datetime import datetime

DB = 'skills/stock-analyzer/scripts/tina_master.db'

TOP100 = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2421','2449','2474','2492','2610','2880','2881','2882',
    '2883','2884','2885','2886','2887','2888','2891','2892','3008','3033',
    '3044','3189','3229','3231','3443','3481','3665','3717','4938','4958',
    '4961','5871','5880','6409','6415','6505','6669','6770','8016','8046',
    '8105','8233','8261','8341','8464','8478','8926','8996','9945','1234',
    '2312','2327','2337','2344','2385','2390','2515','2527','2603','2609'
]

class Version:
    def __init__(self, name, params, desc):
        self.name = name
        self.params = params
        self.desc = desc
        self.trades = []
        self.stats = {}
    
    def check(self, rsi, atr_pct, ma20, ma60, bias, k_cross, macd_bull, inst_foreign, inst_trust, vr):
        p = self.params
        if p['rsi_min'] <= rsi <= p['rsi_max'] and \
           atr_pct >= p['atr_min'] and \
           abs(bias) <= p.get('bias_max', 999) and \
           (not p.get('ma_required') or ma20 > ma60) and \
           (not p.get('k_required') or k_cross) and \
           (not p.get('macd_required') or macd_bull) and \
           (not p.get('inst_both') or (inst_foreign > 0 and inst_trust > 0)) and \
           (not p.get('inst_foreign') or inst_foreign > 0) and \
           vr >= p.get('vr_min', 0):
            return True
        return False

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_kdj(h, i):
    period = 9
    if i < period:
        return 50, 50, False
    lows = [float(h['Low'].iloc[j]) for j in range(i-period, i)]
    highs = [float(h['High'].iloc[j]) for j in range(i-period, i)]
    lo, hi = min(lows), max(highs)
    close = float(h['Close'].iloc[i-1])
    rsv = 50 if hi == lo else (close - lo) / (hi - lo) * 100
    k_vals, d_vals = [], []
    for j in range(period, i):
        lj = min([float(h['Low'].iloc[t]) for t in range(j-period, j)])
        hj = max([float(h['High'].iloc[t]) for t in range(j-period, j)])
        cj = float(h['Close'].iloc[j-1])
        rsvj = 50 if hj == lj else (cj - lj) / (hj - lj) * 100
        k = 50 if len(k_vals) == 0 else 2/3 * k_vals[-1] + 1/3 * rsvj
        d = 50 if len(d_vals) == 0 else 2/3 * d_vals[-1] + 1/3 * k
        k_vals.append(k)
        d_vals.append(d)
    return k_vals[-1], d_vals[-1], k_vals[-1] > d_vals[-1] if len(k_vals) > 1 else (50, False)

def get_macd(closes):
    if len(closes) < 26:
        return 0, False
    ema12, ema26 = [], []
    for i in range(len(closes)):
        e12 = closes[i] if i == 0 else (11/13) * ema12[-1] + (2/13) * closes[i]
        e26 = closes[i] if i == 0 else (25/27) * ema26[-1] + (2/27) * closes[i]
        ema12.append(e12)
        ema26.append(e26)
    macd = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    if len(macd) < 9:
        return 0, False
    return macd[-1], macd[-1] > np.mean(macd[-9:])

def get_vr(h, i):
    if i < 20:
        return 1.0
    av = np.mean([float(h['Volume'].iloc[t]) for t in range(i-5, i)])
    bv = np.mean([float(h['Volume'].iloc[t]) for t in range(i-20, i-5)])
    return av / bv if bv > 0 else 1.0

def get_inst(code, date):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(foreign_net), SUM(trust_net) FROM MarketData
        WHERE symbol = ? AND date <= ? AND date >= date(?, '-3 days')
    ''', (code, date, date))
    f, t = cur.fetchone()
    conn.close()
    return (f or 0), (t or 0)

def collect_trades(version, holding_days=5):
    trades = []
    for code in TOP100:
        try:
            h = yf.Ticker(code + '.TW').history(period='200d')
            if len(h) < 150:
                continue
            closes = list(h['Close'].values)
            for i in range(60, len(closes) - holding_days - 60):
                close = closes[i]
                date = h.index[i].strftime('%Y-%m-%d')
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                bias = (close / ma20 - 1) * 100
                rsi = get_rsi(closes[:i+1])
                hi = float(h['High'].iloc[i])
                lo = float(h['Low'].iloc[i])
                cl_prev = float(h['Close'].iloc[i-1])
                atr = max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev))
                atr_pct = atr / close * 100
                k, d, k_cross = get_kdj(h, i)
                macd_val, macd_bull = get_macd(closes[:i+1])
                vr = get_vr(h, i)
                f_net, t_net = get_inst(code, date)
                if version.check(rsi, atr_pct, ma20, ma60, bias, k_cross, macd_bull, f_net, t_net, vr):
                    future_return = (closes[i+holding_days] / close - 1) * 100
                    trades.append({
                        'code': code, 'date': date, 'return': future_return,
                        'rsi': rsi, 'atr': atr_pct, 'bias': bias, 'vr': vr,
                        'f_net': f_net, 't_net': t_net, 'k_cross': k_cross, 'macd_bull': macd_bull
                    })
        except:
            continue
    return trades

def analyze_stats(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg_return': 0, 'pf': 0, 'mdd': 0}
    wins = [t for t in trades if t['return'] > 0]
    losses = [t for t in trades if t['return'] <= 0]
    win_rate = len(wins) / len(trades) * 100
    avg_return = np.mean([t['return'] for t in trades])
    total_win = sum([t['return'] for t in wins])
    total_loss = abs(sum([t['return'] for t in losses]))
    pf = total_win / total_loss if total_loss > 0 else 0
    # MDD
    returns = sorted([t['return'] for t in trades])
    cum, max_dd, peak = 0, 0, 0
    for r in returns:
        cum += r
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    return {'total': len(trades), 'win_rate': win_rate, 'avg_return': avg_return, 'pf': pf, 'mdd': max_dd}

def analyze_failures(trades):
    failures = [t for t in trades if t['return'] <= 0]
    if not failures:
        return {}
    reasons = {
        'RSI>70': 0, 'RSI<30': 0, 'ATR<0.5': 0, 'Bias>5%': 0, 'Bias<-5%': 0,
        'VR<1': 0, 'MA空頭': 0, '法人賣超': 0, 'KDJ死叉': 0, 'MACD空頭': 0
    }
    for t in failures:
        if t['rsi'] > 70: reasons['RSI>70'] += 1
        if t['rsi'] < 30: reasons['RSI<30'] += 1
        if t['atr'] < 0.5: reasons['ATR<0.5'] += 1
        if t['bias'] > 5: reasons['Bias>5%'] += 1
        if t['bias'] < -5: reasons['Bias<-5%'] += 1
        if t['vr'] < 1: reasons['VR<1'] += 1
        if t['bias'] < 0: reasons['MA空頭'] += 1
        if t['f_net'] < 0 and t['t_net'] < 0: reasons['法人賣超'] += 1
        if not t['k_cross']: reasons['KDJ死叉'] += 1
        if not t['macd_bull']: reasons['MACD空頭'] += 1
    total_fail = len(failures)
    return {k: round(v/total_fail*100, 1) for k, v in sorted(reasons.items(), key=lambda x: -x[1]) if v > 0}

# 版本歷史
version_history = []

# 初始版本
v1 = Version('v1_base', {
    'rsi_min': 0, 'rsi_max': 70,
    'atr_min': 0.5,
    'bias_max': 10,
    'ma_required': False,
    'k_required': False,
    'macd_required': False,
    'inst_both': False,
    'inst_foreign': False,
    'vr_min': 0
}, '基準版本 v4.21')

version_history.append(v1)

print('='*70)
print(' Tina v4.21 失敗分析與自動迭代優化系統')
print('='*70)
print()
print(' 開始迭代優化...')
print()

iteration = 1
max_iterations = 10
current_best = v1

while iteration <= max_iterations:
    print('【迭代 ' + str(iteration) + '】')
    
    # 收集交易
    trades = collect_trades(current_best, 5)
    stats = analyze_stats(trades)
    failures = analyze_failures(trades)
    
    print('  版本: ' + current_best.name)
    print('  交易次: ' + str(stats['total']) + ' | 勝率: ' + str(round(stats['win_rate'],1)) + '%')
    print('  平均報酬: ' + str(round(stats['avg_return'],2)) + '% | PF: ' + str(round(stats['pf'],2)))
    
    if failures:
        print('  失敗原因:')
        for k, v in failures.items():
            print('    - ' + k + ': ' + str(v) + '%')
    
    # 分析並提出修改建議
    if iteration == 1:
        # 根據失敗原因提出修改
        modifications = []
        
        # 分析失敗原因，提出修改
        if 'RSI>70' in failures and failures['RSI>70'] > 20:
            modifications.append(('rsi_max', 65, '降低 RSI 上限'))
        
        if 'VR<1' in failures and failures['VR<1'] > 15:
            modifications.append(('vr_min', 1.0, '增加 VR 篩選'))
        
        if 'Bias>5%' in failures and failures['Bias>5%'] > 10:
            modifications.append(('bias_max', 5, '降低 Bias 上限'))
        
        if 'MACD空頭' in failures and failures['MACD空頭'] > 20:
            modifications.append(('macd_required', True, '增加 MACD 多頭條件'))
        
        if 'KDJ死叉' in failures and failures['KDJ死叉'] > 25:
            modifications.append(('k_required', True, '增加 KDJ 金叉條件'))
        
        if '法人賣超' in failures and failures['法人賣超'] > 15:
            modifications.append(('inst_foreign', True, '增加外資買超條件'))
        
        if not modifications:
            modifications.append(('ma_required', True, '增加 MA20>MA60 條件'))
        
        print()
        print('  建議修改:')
        for m in modifications:
            print('    - ' + m[2])
        
        # 創建新版本
        new_params = current_best.params.copy()
        for m in modifications:
            new_params[m[0]] = m[1]
        
        new_version = Version(
            'v' + str(iteration + 1) + '_mod',
            new_params,
            '; '.join([m[2] for m in modifications])
        )
        
        print()
        print('  建立新版本: ' + new_version.name)
        
    else:
        # 延續上次修改
        new_version = current_best
    
    # 回測新版本
    new_trades = collect_trades(new_version, 5)
    new_stats = analyze_stats(new_trades)
    
    print()
    print('  新版本測試結果:')
    print('    交易次: ' + str(stats['total']) + ' -> ' + str(new_stats['total']))
    print('    勝率: ' + str(round(stats['win_rate'],1)) + '% -> ' + str(round(new_stats['win_rate'],1)) + '%')
    print('    PF: ' + str(round(stats['pf'],2)) + ' -> ' + str(round(new_stats['pf'],2)))
    
    # 比較
    improved = new_stats['win_rate'] > stats['win_rate'] and new_stats['total'] >= stats['total'] * 0.5
    same_or_better = new_stats['win_rate'] >= stats['win_rate'] - 1 and new_stats['pf'] >= stats['pf'] - 0.1
    
    if improved or same_or_better:
        print()
        print('  結論: ✅ 接受新版本 ' + new_version.name)
        new_version.trades = new_trades
        new_version.stats = new_stats
        version_history.append(new_version)
        current_best = new_version
        
        if new_stats['win_rate'] >= 60 and new_stats['total'] >= 500:
            print()
            print('  達成目標，停止迭代')
            break
    else:
        print()
        print('  結論: ❌ 拒絕新版本，維持 ' + current_best.name)
    
    print()
    iteration += 1

print('='*70)
print(' 迭代完成')
print('='*70)
print()

# 最終結果
final_stats = analyze_stats(collect_trades(current_best, 5))
final_failures = analyze_failures(collect_trades(current_best, 5))

print('[最終版本]: ' + current_best.name)
print('[修正概要]: ' + current_best.desc)
print()
print('【最終績效】')
print('  交易次: ' + str(final_stats['total']))
print('  勝率: ' + str(round(final_stats['win_rate'],1)) + '%')
print('  平均報酬: ' + str(round(final_stats['avg_return'],2)) + '%')
print('  PF: ' + str(round(final_stats['pf'],2)) + '%')
print('  MDD: ' + str(round(final_stats['mdd'],2)) + '%')
print()

if final_failures:
    print('【最終失敗原因分析】')
    for k, v in final_failures.items():
        print('  ' + k + ': ' + str(v) + '%')
print()

print('【版本歷史】')
for v in version_history:
    print('  - ' + v.name + ': ' + v.desc)
print()
print('='*70)

# 儲存結果
result = {
    'final_version': current_best.name,
    'desc': current_best.desc,
    'stats': final_stats,
    'failures': final_failures,
    'history': [(v.name, v.desc) for v in version_history]
}
with open('Tina_Quant_System/logs/iterative_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(' 結果已儲存: logs/iterative_result.json')