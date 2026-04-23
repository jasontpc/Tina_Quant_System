# -*- coding: utf-8 -*-
"""
Tina v4.21 Advanced Iteration - 法人權重 + RSI動態化
股票池: 台股市值前100大
回測區間: 滾動120日
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import json

DB = 'skills/stock-analyzer/scripts/tina_master.db'

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

def get_rsi_slope(closes, period=5):
    """RSI 斜率 (5日變化)"""
    if len(closes) < 14 + period:
        return 0
    rsi_now = get_rsi(closes)
    rsi_prev = get_rsi(closes[:-period])
    return rsi_now - rsi_prev

def get_rsi_accel(closes, period=3):
    """RSI 二階導數 (加速度)"""
    if len(closes) < 14 + period * 2:
        return 0
    slope_now = get_rsi_slope(closes, period)
    slope_prev = get_rsi_slope(closes[:-period], period)
    return slope_now - slope_prev

def get_atr(h, i):
    if i < 1:
        return 0
    hi = float(h['High'].iloc[i])
    lo = float(h['Low'].iloc[i])
    cl = float(h['Close'].iloc[i-1])
    return max(hi-lo, abs(hi-cl), abs(lo-cl))

def get_inst(code):
    """取得法人淨買賣"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(foreign_net), SUM(trust_net) FROM MarketData
        WHERE symbol = ? AND date >= date("now", "-3 days")
    ''', (code,))
    f, t = cur.fetchone()
    conn.close()
    return (f or 0), (t or 0)

def get_inst_weight(f_net, t_net):
    """法人權重因子 (0.5 ~ 1.5)"""
    total = f_net + t_net
    # 法人大買 -> 權重 1.5
    # 法人持平 -> 權重 1.0
    # 法人大賣 -> 權重 0.5
    if total > 5000:  # 大於5張
        return 1.5
    elif total > 0:
        return 1.0 + (total / 10000)  # 線性
    elif total > -5000:
        return 0.5 + (total / -10000)  # 線性
    else:
        return 0.5

def check_rsi_dynamic(rsi, closes):
    """動態 RSI 判斷"""
    # 基本條件
    if rsi > 80:
        slope = get_rsi_slope(closes, 5)
        accel = get_rsi_accel(closes, 3)
        # RSI>80 但動能續強 -> 可進場
        if slope > 5 and accel > 2:
            return True
        return False
    
    if rsi > 70:
        slope = get_rsi_slope(closes, 5)
        accel = get_rsi_accel(closes, 3)
        # RSI 70-80，動能放緩 -> 不進場
        if slope < 0 and accel < -1:
            return False
        # RSI 70-80，動能持續 -> 可進場
        if slope > 3:
            return True
        return False
    
    # RSI < 70 -> 可進場
    return True

def backtest_version(version_name, params, holding=5):
    """回測單一版本"""
    trades = []
    
    for code in STOCKS:
        try:
            h = yf.Ticker(code + '.TW').history(period='180d')
            if len(h) < 120:
                continue
            
            closes = list(h['Close'].values)
            
            for i in range(60, len(closes) - holding - 20):
                close = closes[i]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                
                f_net, t_net = get_inst(code)
                
                # === 版本條件 ===
                if version_name == 'v1_base':
                    ok = rsi < 70 and atr_pct >= 0.5 and ma20 > ma60
                    weight = 1.0
                    
                elif version_name == 'v2_inst_weight':
                    ok = rsi < 70 and atr_pct >= 0.5 and ma20 > ma60
                    weight = get_inst_weight(f_net, t_net)
                    
                elif version_name == 'v3_rsi_dynamic':
                    ok = check_rsi_dynamic(rsi, closes[:i+1]) and atr_pct >= 0.5 and ma20 > ma60
                    weight = 1.0
                    
                elif version_name == 'v4_full':
                    ok = check_rsi_dynamic(rsi, closes[:i+1]) and atr_pct >= 0.5 and ma20 > ma60
                    weight = get_inst_weight(f_net, t_net)
                    
                elif version_name == 'v5_full_bias':
                    # 加入 Bias 篩選
                    bias = (close / ma20 - 1) * 100
                    ok = check_rsi_dynamic(rsi, closes[:i+1]) and atr_pct >= 0.5 and ma20 > ma60 and abs(bias) < 5
                    weight = get_inst_weight(f_net, t_net)
                
                else:
                    ok = False
                    weight = 1.0
                
                if ok:
                    ret = (closes[i+holding] / close - 1) * 100
                    # 根據權重調整報酬 (法人大買放大報酬)
                    adjusted_ret = ret * weight
                    trades.append({
                        'code': code,
                        'return': ret,
                        'adjusted_return': adjusted_ret,
                        'weight': weight,
                        'rsi': rsi,
                        'f_net': f_net,
                        't_net': t_net
                    })
        except:
            continue
    
    return trades

def analyze(trades, use_adjusted=False):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg': 0, 'pf': 0, 'mdd': 0}
    
    returns = [t['adjusted_return'] if use_adjusted else t['return'] for t in trades]
    
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    total = len(returns)
    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg = np.mean(returns) if total > 0 else 0
    
    total_win = sum(wins)
    total_loss = abs(sum(losses))
    pf = total_win / total_loss if total_loss > 0 else 0
    
    # MDD
    sorted_ret = sorted(returns)
    cum, max_dd, peak = 0, 0, 0
    for r in sorted_ret:
        cum += r
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    
    return {'total': total, 'win_rate': win_rate, 'avg': avg, 'pf': pf, 'mdd': max_dd}

def analyze_failures(trades):
    """分析失敗原因"""
    failures = [t for t in trades if t['return'] <= 0]
    if not failures:
        return {}
    
    reasons = {
        'RSI>80': 0, 'RSI>70-80': 0, 'Bias>5%': 0,
        '法人賣超': 0, 'ATR不足': 0, 'MA空頭': 0
    }
    
    for t in failures:
        rsi = t['rsi']
        if rsi > 80:
            reasons['RSI>80'] += 1
        elif rsi > 70:
            reasons['RSI>70-80'] += 1
        
        bias = (t['return'])  # 簡化
        if t['f_net'] < 0 and t['t_net'] < 0:
            reasons['法人賣超'] += 1
    
    total = len(failures)
    return {k: round(v/total*100, 1) for k, v in sorted(reasons.items(), key=lambda x: -x[1]) if v > 0}

def main():
    print('='*60)
    print(' Tina v4.21 Advanced Iteration')
    print(' 法人權重 + RSI動態化')
    print('='*60)
    
    versions = [
        ('v1_base', '基準 v4.21'),
        ('v2_inst_weight', '+法人權重'),
        ('v3_rsi_dynamic', '+RSI動態化'),
        ('v4_full', '+法人權重+RSI動態化'),
        ('v5_full_bias', '+Bias篩選'),
    ]
    
    results = []
    
    for name, desc in versions:
        print()
        print(' 測試 ' + name + ' (' + desc + ')...')
        trades = backtest_version(name, {})
        
        # 基本分析
        stats_raw = analyze(trades, use_adjusted=False)
        stats_adj = analyze(trades, use_adjusted=True)
        
        print('    原始: ' + str(stats_raw['total']) + '筆 ' + str(round(stats_raw['win_rate'],1)) + '% WR, ' +
              str(round(stats_raw['avg'],2)) + '% avg, PF=' + str(round(stats_raw['pf'],2)))
        print('    調整: ' + str(stats_adj['total']) + '筆 ' + str(round(stats_adj['win_rate'],1)) + '% WR, ' +
              str(round(stats_adj['avg'],2)) + '% avg, PF=' + str(round(stats_adj['pf'],2)))
        
        # 失敗分析
        failures = analyze_failures(trades)
        if failures:
            print('    失敗: ' + ', '.join([k + '=' + str(v) + '%' for k, v in failures.items()]))
        
        results.append({
            'name': name,
            'desc': desc,
            'trades': trades,
            'stats_raw': stats_raw,
            'stats_adj': stats_adj,
            'failures': failures
        })
    
    print()
    print('='*60)
    print(' 版本比較')
    print('='*60)
    print()
    print('%-12s %-20s %-8s %-8s %-8s %-8s' % ('版本', '說明', '交易次', '勝率', '平均', 'PF'))
    print('-'*60)
    
    # 使用調整後報酬排序
    results.sort(key=lambda x: (x['stats_adj']['win_rate'], x['stats_adj']['total']), reverse=True)
    
    for r in results:
        s = r['stats_adj']
        print('%-12s %-20s %-8d %-8.1f %-8.2f %-8.2f' % (
            r['name'], r['desc'], s['total'], s['win_rate'], s['avg'], s['pf']))
    
    # 最佳版本
    best = results[0]
    base = results[0]  # v1_base 實際是第一個
    
    print()
    print('='*60)
    print(' 版本控制决策')
    print('='*60)
    print()
    print('[最佳版本]: ' + best['name'] + ' (' + best['desc'] + ')')
    print()
    print('【績效對比 vs 基準】')
    print(' 勝率: ' + str(round(base['stats_adj']['win_rate'],1)) + '% -> ' +
          str(round(best['stats_adj']['win_rate'],1)) + '%')
    print(' 交易次: ' + str(base['stats_adj']['total']) + ' -> ' +
          str(best['stats_adj']['total']))
    print(' 平均報酬: ' + str(round(base['stats_adj']['avg'],2)) + '% -> ' +
          str(round(best['stats_adj']['avg'],2)) + '%')
    print(' PF: ' + str(round(base['stats_adj']['pf'],2)) + ' -> ' +
          str(round(best['stats_adj']['pf'],2)))
    print()
    
    # 失敗原因
    if best['failures']:
        print('【失敗原因分析】')
        for k, v in best['failures'].items():
            print('  ' + k + ': ' + str(v) + '%')
        print()
    
    # 後續行動
    win_rate_chg = best['stats_adj']['win_rate'] - base['stats_adj']['win_rate']
    total_chg = best['stats_adj']['total'] - base['stats_adj']['total']
    
    print('【後續行動】')
    if win_rate_chg > 1 and total_chg > -200:
        print(' ✅ 接受新版本: ' + best['name'])
        print('    - 勝率提升 ' + str(round(win_rate_chg,1)) + '%')
        print('    - 交易次變化 ' + str(total_chg))
    elif win_rate_chg >= -0.5:
        print(' ⚠️ 勝率持平，維持 v4.21')
    else:
        print(' ❌ 績效劣化，維持 v4.21')
        print('    - 勝率下降 ' + str(round(abs(win_rate_chg),1)) + '%')
    
    # 法人權重分析
    print()
    print('='*60)
    print(' 法人權重效果分析')
    print('='*60)
    
    v2 = next((r for r in results if r['name'] == 'v2_inst_weight'), None)
    v4 = next((r for r in results if r['name'] == 'v4_full'), None)
    
    if v2 and v4:
        print()
        print(' v2 (法人權重): ' + str(round(v2['stats_adj']['win_rate'],1)) + '% WR')
        print(' v4 (法人權重+RSI動態): ' + str(round(v4['stats_adj']['win_rate'],1)) + '% WR')
        
        if v4['stats_adj']['win_rate'] > v2['stats_adj']['win_rate']:
            print(' 結論: RSI動態化 + 法人權重效果最好')
        else:
            print(' 結論: 法人權重為主要提升因素')
    
    print()
    print('='*60)
    
    # 儲存
    result_save = {
        'best_version': best['name'],
        'desc': best['desc'],
        'stats': best['stats_adj'],
        'failures': best['failures'],
        'all_results': [(r['name'], r['desc'], r['stats_adj']) for r in results]
    }
    with open('Tina_Quant_System/logs/advanced_iteration.json', 'w', encoding='utf-8') as f:
        json.dump(result_save, f, ensure_ascii=False, indent=2)
    print(' 已儲存: logs/advanced_iteration.json')

if __name__ == '__main__':
    main()