# -*- coding: utf-8 -*-
"""
Tina v4.21 滾動式回測系統
版本控制 + 自動迭代優化
股票池: 台股市值前100大
回測區間: 滾動120日
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import json
from datetime import datetime, timedelta

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# Top 100 (常見大型股)
TOP100 = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2421','2449','2474','2492','2610','2880','2881','2882',
    '2883','2884','2885','2886','2887','2888','2891','2892','3008','3033',
    '3044','3189','3229','3231','3443','3481','3665','3717','4938','4958',
    '4961','5871','5880','6409','6415','6505','6669','6770','8016','8046',
    '8105','8233','8261','8341','8464','8478','8926','8996','9945','1234',
    '2312','2327','2337','2344','2385','2390','2515','2527','2603','2609',
    '2707','2823','2834','2855','2912','2939','3029','3045','3088','3105',
    '3234','3257','3294','3305','3380','3416','3443','3533','3557','3593',
    '3596','3610','3673','3686','3702','3711','3722','4001','4002','4904'
]

class Version:
    def __init__(self, name, params):
        self.name = name
        self.params = params
    
    def check(self, rsi, atr_pct, ma20, ma60, k_cross, macd_bull, inst_foreign, inst_trust, bias, vr):
        p = self.params
        if p['rsi_min'] <= rsi <= p['rsi_max'] and \
           atr_pct >= p['atr_min'] and \
           (not p.get('ma20_above_ma60') or ma20 > ma60) and \
           (not p.get('k_cross') or k_cross) and \
           (not p.get('macd_bull') or macd_bull) and \
           (not p.get('inst_both') or (inst_foreign > 0 and inst_trust > 0)) and \
           (not p.get('inst_any') or (inst_foreign > 0 or inst_trust > 0)) and \
           abs(bias) <= p.get('bias_max', 999) and \
           vr >= p.get('vr_min', 0):
            return True
        return False

# 版本定義
VERSIONS = {
    'v4.21': Version('v4.21', {
        'rsi_min': 0, 'rsi_max': 70,
        'atr_min': 0.5,
        'ma20_above_ma60': True,
        'inst_any': True,
        'bias_max': 10,
        'vr_min': 0
    }),
    'v4.21_kdj': Version('v4.21_kdj', {
        'rsi_min': 0, 'rsi_max': 70,
        'atr_min': 0.5,
        'ma20_above_ma60': True,
        'k_cross': True,
        'inst_any': True,
        'bias_max': 10,
        'vr_min': 0
    }),
    'v4.21_kdj_macd': Version('v4.21_kdj_macd', {
        'rsi_min': 0, 'rsi_max': 70,
        'atr_min': 0.5,
        'ma20_above_ma60': True,
        'k_cross': True,
        'macd_bull': True,
        'inst_any': True,
        'bias_max': 10,
        'vr_min': 0
    }),
    'v4.21_inst_both': Version('v4.21_inst_both', {
        'rsi_min': 0, 'rsi_max': 70,
        'atr_min': 0.5,
        'ma20_above_ma60': True,
        'inst_both': True,
        'bias_max': 10,
        'vr_min': 0
    }),
    'v4.21_vr': Version('v4.21_vr', {
        'rsi_min': 0, 'rsi_max': 70,
        'atr_min': 0.5,
        'ma20_above_ma60': True,
        'inst_any': True,
        'bias_max': 5,
        'vr_min': 1.0
    }),
    'v4.21_relax': Version('v4.21_relax', {
        'rsi_min': 30, 'rsi_max': 75,
        'atr_min': 0.3,
        'ma20_above_ma60': False,
        'inst_any': True,
        'bias_max': 15,
        'vr_min': 0
    }),
}

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
    
    lo = min(lows)
    hi = max(highs)
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
    
    k = k_vals[-1] if k_vals else 50
    d = d_vals[-1] if d_vals else 50
    k_cross = k_vals[-1] > d_vals[-1] if len(k_vals) > 1 else False
    return k, d, k_cross

def get_macd(closes):
    if len(closes) < 26:
        return 0, 0, False
    ema12, ema26 = [], []
    for i in range(len(closes)):
        e12 = closes[i] if i == 0 else (11/13) * ema12[-1] + (2/13) * closes[i]
        e26 = closes[i] if i == 0 else (25/27) * ema26[-1] + (2/27) * closes[i]
        ema12.append(e12)
        ema26.append(e26)
    macd = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    if len(macd) < 9:
        return 0, 0, False
    macd_val = macd[-1]
    macd_signal = np.mean(macd[-9:])
    return macd_val, macd_signal, macd_val > macd_signal

def get_atr(h, i):
    trs = []
    for j in range(max(0, i-14), i):
        hi = float(h['High'].iloc[j])
        lo = float(h['Low'].iloc[j])
        cl = float(h['Close'].iloc[j-1]) if j-1 >= 0 else float(h['Close'].iloc[j])
        trs.append(max(hi-lo, abs(hi-cl), abs(lo-cl)))
    return np.mean(trs) if trs else 0

def get_vr(closes, h, i):
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
    f_sum, t_sum = cur.fetchone()
    conn.close()
    return (f_sum or 0), (t_sum or 0)

def rolling_backtest(version_name, holding_days=5):
    version = VERSIONS[version_name]
    trades = []
    
    for code in TOP100:
        try:
            h = yf.Ticker(code + '.TW').history(period='200d')
            if len(h) < 150:
                continue
            
            closes = list(h['Close'].values)
            
            # 滾動120日回測
            for i in range(60, len(closes) - holding_days - 60):
                close = closes[i]
                date = h.index[i].strftime('%Y-%m-%d')
                
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                bias = (close / ma20 - 1) * 100
                
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                
                k, d, k_cross = get_kdj(h, i)
                macd_val, macd_signal, macd_bull = get_macd(closes[:i+1])
                
                vr = get_vr(closes, h, i)
                
                f_net, t_net = get_inst(code, date)
                
                if version.check(rsi, atr_pct, ma20, ma60, k_cross, macd_bull, f_net, t_net, bias, vr):
                    future_return = (closes[i+holding_days] / close - 1) * 100
                    trades.append({
                        'code': code,
                        'date': date,
                        'return': future_return,
                        'rsi': rsi,
                        'atr': atr_pct
                    })
        except:
            continue
    
    return trades

def analyze_trades(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg_return': 0, 'pf': 0, 'mdd': 0}
    
    total = len(trades)
    wins = [t for t in trades if t['return'] > 0]
    losses = [t for t in trades if t['return'] <= 0]
    
    win_rate = len(wins) / total * 100
    avg_return = np.mean([t['return'] for t in trades])
    avg_win = np.mean([t['return'] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t['return'] for t in losses])) if losses else 0
    
    total_win = sum([t['return'] for t in wins])
    total_loss = abs(sum([t['return'] for t in losses]))
    pf = total_win / total_loss if total_loss > 0 else 0
    
    # MDD
    returns = sorted([t['return'] for t in trades])
    cum = 0
    max_dd = 0
    peak = 0
    for r in returns:
        cum += r
        peak = max(peak, cum)
        dd = peak - cum
        max_dd = max(max_dd, dd)
    
    return {
        'total': total,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'pf': pf,
        'mdd': max_dd
    }

# ==================== 主程式 ====================
print('='*70)
print(' Tina v4.21 滾動式回測系統')
print(' 股票池: 台股市值前100大')
print(' 回測區間: 滾動120日')
print('='*70)

results = {}
print()
print(' 開始回測各版本...')
print()

for v_name in VERSIONS.keys():
    print(' 測試 ' + v_name + '...')
    trades = rolling_backtest(v_name, 5)
    stats = analyze_trades(trades)
    results[v_name] = {
        'trades': trades,
        'stats': stats,
        'version': v_name
    }

# 排序
sorted_versions = sorted(results.keys(), key=lambda v: results[v]['stats']['win_rate'], reverse=True)

print()
print('='*70)
print(' 版本比較結果')
print('='*70)
print()
print('%-15s %-8s %-8s %-10s %-8s %-8s %-8s' % (
    '版本', '交易次', '勝率', '平均報酬', '平均獲利', 'PF', 'MDD'))
print('-'*70)

for v in sorted_versions:
    s = results[v]['stats']
    print('%-15s %-8d %-8.1f %-10.2f %-8.2f %-8.2f %-8.2f' % (
        v, s['total'], s['win_rate'], s['avg_return'], s['avg_win'], s['pf'], s['mdd']))

# 版本控制邏輯
print()
print('='*70)
print(' 版本控制决策')
print('='*70)
print()

current_best = sorted_versions[0]
current_stats = results[current_best]['stats']

print('[版本序號]: ' + current_best)
print('[修正概要]: ' + current_best + ' 參數優化')
print()
print('【績效對比】')
print('  vs  v4.21 (基準):')
v421_stats = results['v4.21']['stats']
print('   勝率變化: ' + str(round(v421_stats['win_rate'],1)) + '% -> ' + str(round(current_stats['win_rate'],1)) + '% (' +
      ('+' if current_stats['win_rate'] > v421_stats['win_rate'] else '') + str(round(current_stats['win_rate'] - v421_stats['win_rate'],1)) + '%)')
print('   交易次變化: ' + str(v421_stats['total']) + ' -> ' + str(current_stats['total']) + ' (' +
      ('+' if current_stats['total'] > v421_stats['total'] else '') + str(current_stats['total'] - v421_stats['total']) + ')')
print('   MDD 變化: ' + str(round(v421_stats['mdd'],2)) + '% -> ' + str(round(current_stats['mdd'],2)) + '% (' +
      ('+' if current_stats['mdd'] < v421_stats['mdd'] else '') + str(round(current_stats['mdd'] - v421_stats['mdd'],2)) + '%)')
print('   PF 變化: ' + str(round(v421_stats['pf'],2)) + ' -> ' + str(round(current_stats['pf'],2)) + ' (' +
      ('+' if current_stats['pf'] > v421_stats['pf'] else '') + str(round(current_stats['pf'] - v421_stats['pf'],2)) + ')')

print()
print('【後續行動】')
if current_stats['win_rate'] > v421_stats['win_rate'] and current_stats['avg_return'] >= v421_stats['avg_return']:
    print(' ✅ 績效提升，更新為主版本')
    print('    - 勝率提升 ' + str(round(current_stats['win_rate'] - v421_stats['win_rate'],1)) + '%')
    print('    - 期望值 ' + str(round(current_stats['avg_return'],2)) + '%')
elif current_stats['win_rate'] >= v421_stats['win_rate'] - 2:
    print(' ⚠️ 績效持平，維持 v4.21')
else:
    print(' ❌ 績效劣化，Rollback 至 v4.21')
    print('    - 勝率下降 ' + str(round(v421_stats['win_rate'] - current_stats['win_rate'],1)) + '%')

print()
print('='*70)

# 輸出 TOP5 交易
print()
print('【' + current_best + ' TOP5 交易】')
trades = results[current_best]['trades']
trades.sort(key=lambda x: x['return'], reverse=True)
for i, t in enumerate(trades[:5], 1):
    icon = '▲' if t['return'] > 0 else '▼'
    print(' ' + str(i) + '. ' + t['code'] + ' ' + t['date'] + ' ' + icon + str(round(abs(t['return']),1)) + '% RSI=' + str(round(t['rsi'])))

print()
print('='*70)