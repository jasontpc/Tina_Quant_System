# -*- coding: utf-8 -*-
"""
Tina v4.21 快速迭代優化 - 精簡版
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import json

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# 精簡股票池 (主要大型股)
STOCKS = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2492','2610','2880','2881','2882','2883','2884','2885',
    '2886','2887','2891','2892','3008','3033','3044','3189','3231','3443',
    '3481','3665','3717','4938','4958','6415','6505','6669','6770','8016',
    '8046','8105','8261','8341','8464','8926','8996','9945','2385','2603'
]

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_atr(h, i):
    if i < 1:
        return 0
    hi = float(h['High'].iloc[i])
    lo = float(h['Low'].iloc[i])
    cl = float(h['Close'].iloc[i-1])
    return max(hi-lo, abs(hi-cl), abs(lo-cl))

def get_inst(code):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT SUM(foreign_net), SUM(trust_net) FROM MarketData WHERE symbol = ? AND date >= date("now", "-5 days")', (code,))
    f, t = cur.fetchone()
    conn.close()
    return (f or 0), (t or 0)

def backtest(params, holding=5):
    trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code + '.TW').history(period='180d')
            if len(h) < 120:
                continue
            closes = list(h['Close'].values)
            for i in range(60, len(closes) - holding - 30):
                close = closes[i]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                bias = (close / ma20 - 1) * 100
                f_net, t_net = get_inst(code)
                
                # 條件
                ok = params['rsi_min'] <= rsi <= params['rsi_max']
                ok = ok and atr_pct >= params['atr_min']
                ok = ok and abs(bias) <= params['bias_max']
                if params.get('ma_req'):
                    ok = ok and ma20 > ma60
                if params.get('inst_f'):
                    ok = ok and f_net > 0
                if params.get('inst_both'):
                    ok = ok and f_net > 0 and t_net > 0
                
                if ok:
                    ret = (closes[i+holding] / close - 1) * 100
                    trades.append(ret)
        except:
            continue
    return trades

def stats(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg': 0, 'pf': 0}
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    total = len(trades)
    wr = len(wins) / total * 100 if total > 0 else 0
    avg = np.mean(trades) if total > 0 else 0
    pf = abs(sum(wins) / sum(losses)) if losses else 0
    return {'total': total, 'win_rate': wr, 'avg': avg, 'pf': pf}

print('='*60)
print(' Tina v4.21 快速迭代優化')
print('='*60)

# 測試各版本
versions = [
    ('v1_base', {'rsi_min': 0, 'rsi_max': 70, 'atr_min': 0.5, 'bias_max': 10, 'ma_req': False, 'inst_f': False, 'inst_both': False}, '基準'),
    ('v2_ma', {'rsi_min': 0, 'rsi_max': 70, 'atr_min': 0.5, 'bias_max': 10, 'ma_req': True, 'inst_f': False, 'inst_both': False}, '+MA20>MA60'),
    ('v3_inst', {'rsi_min': 0, 'rsi_max': 70, 'atr_min': 0.5, 'bias_max': 10, 'ma_req': False, 'inst_f': True, 'inst_both': False}, '+外資買超'),
    ('v4_both', {'rsi_min': 0, 'rsi_max': 70, 'atr_min': 0.5, 'bias_max': 10, 'ma_req': False, 'inst_f': False, 'inst_both': True}, '+雙法買超'),
    ('v5_rsi65', {'rsi_min': 0, 'rsi_max': 65, 'atr_min': 0.5, 'bias_max': 10, 'ma_req': False, 'inst_f': False, 'inst_both': False}, 'RSI<65'),
    ('v6_bias5', {'rsi_min': 0, 'rsi_max': 70, 'atr_min': 0.5, 'bias_max': 5, 'ma_req': False, 'inst_f': False, 'inst_both': False}, 'Bias<5%'),
    ('v7_combo', {'rsi_min': 0, 'rsi_max': 65, 'atr_min': 0.5, 'bias_max': 5, 'ma_req': True, 'inst_f': True, 'inst_both': False}, 'Combo 1'),
    ('v8_full', {'rsi_min': 0, 'rsi_max': 65, 'atr_min': 0.5, 'bias_max': 5, 'ma_req': True, 'inst_f': False, 'inst_both': True}, 'Combo 2'),
]

results = []
for name, params, desc in versions:
    print(' 測試 ' + name + ' (' + desc + ')...')
    trades = backtest(params)
    s = stats(trades)
    results.append((name, desc, s))
    print('    交易: ' + str(s['total']) + ' | 勝率: ' + str(round(s['win_rate'],1)) + '% | 平均: ' + str(round(s['avg'],2)) + '% | PF: ' + str(round(s['pf'],2)))

print()
print('='*60)
print(' 結果排序')
print('='*60)
print()
print('%-10s %-12s %-8s %-8s %-8s %-8s' % ('版本', '說明', '交易次', '勝率', '平均報酬', 'PF'))
print('-'*60)

results.sort(key=lambda x: (x[2]['win_rate'], x[2]['total']), reverse=True)

for name, desc, s in results:
    print('%-10s %-12s %-8d %-8.1f %-8.2f %-8.2f' % (name, desc, s['total'], s['win_rate'], s['avg'], s['pf']))

print()
print('='*60)

# 最佳版本
best = results[0]
base = results[0]  # v1_base

print('[最佳版本]: ' + best[0])
print('[說明]: ' + best[1])
print()
print('【績效對比 vs 基準】')
print(' 勝率: ' + str(round(base[2]['win_rate'],1)) + '% -> ' + str(round(best[2]['win_rate'],1)) + '%')
print(' 交易次: ' + str(base[2]['total']) + ' -> ' + str(best[2]['total']))
print(' 平均報酬: ' + str(round(base[2]['avg'],2)) + '% -> ' + str(round(best[2]['avg'],2)) + '%')
print(' PF: ' + str(round(base[2]['pf'],2)) + ' -> ' + str(round(best[2]['pf'],2)))
print()

# 失敗分析
if best[2]['total'] > 0:
    all_trades = backtest(versions[0][1])  # base
    fail = [t for t in all_trades if t <= 0]
    if fail:
        print('【失敗原因分析 (基準)】')
        print(' 失敗筆數: ' + str(len(fail)))
        print(' 失敗率: ' + str(round(100 - results[0][2]['win_rate'], 1)) + '%')
        print()

print('【後續行動】')
if best[2]['win_rate'] > base[2]['win_rate'] + 2:
    print(' ✅ 勝率提升，更新為主版本')
elif best[2]['win_rate'] >= base[2]['win_rate'] - 1:
    print(' ⚠️ 勝率持平，維持 v4.21')
else:
    print(' ❌ 績效劣化，維持 v4.21')

print()
print('='*60)

# 儲存
result = {
    'best_version': best[0],
    'desc': best[1],
    'stats': best[2],
    'all_results': [(n, d, s) for n, d, s in results]
}
with open('Tina_Quant_System/logs/iterative_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(' 已儲存: logs/iterative_result.json')