# -*- coding: utf-8 -*-
"""
Tina v4.21 動態出场策略 - 迭代優化
目標: 提升勝率與交易數量
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

def get_atr(h, i):
    if i < 1:
        return 0
    hi = float(h['High'].iloc[i])
    lo = float(h['Low'].iloc[i])
    cl = float(h['Close'].iloc[i-1])
    return max(hi-lo, abs(hi-cl), abs(lo-cl))

def get_kdj(h, i):
    period = 9
    if i < period:
        return 50, False
    lows = [float(h['Low'].iloc[j]) for j in range(i-period, i)]
    highs = [float(h['High'].iloc[j]) for j in range(i-period, i)]
    lo, hi = min(lows), max(highs)
    close = float(h['Close'].iloc[i-1])
    rsv = 50 if hi == lo else (close - lo) / (hi - lo) * 100
    k = 50
    for j in range(period, i):
        lj = min([float(h['Low'].iloc[t]) for t in range(j-period, j)])
        hj = max([float(h['High'].iloc[t]) for t in range(j-period, j)])
        cj = float(h['Close'].iloc[j-1])
        rsvj = 50 if hj == lj else (cj - lj) / (hj - lj) * 100
        k = 2/3 * k + 1/3 * rsvj
    return k, k > 50

def get_inst(code):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(foreign_net), SUM(trust_net) FROM MarketData
        WHERE symbol = ? AND date >= date('now', '-5 days')
    ''', (code,))
    f, t = cur.fetchone()
    conn.close()
    return (f or 0), (t or 0)

def backtest(exit_config, holding=5):
    """
    exit_config: {
        'name': str,
        'atr_mult': float,  # ATR 倍數
        'trailing': bool,   # 是否使用移動停損
        'time_max': int,    # 最大持有天數
        'profit_target': float,  # 獲利目標 % (None = 不設)
        'stop_loss': float,     # 停損 % (None = 不設)
        'rsi_exit': tuple      # (RSI高門檻, RSI低門檻) 或 None
    }
    """
    trades = []
    
    for code in STOCKS:
        try:
            h = yf.Ticker(code + '.TW').history(period='200d')
            if len(h) < 120:
                continue
            
            closes = list(h['Close'].values)
            highs = list(h['High'].values)
            lows = list(h['Low'].values)
            
            for i in range(60, len(closes) - holding - 20):
                close = closes[i]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                
                k, k_cross = get_kdj(h, i)
                
                f_net, t_net = get_inst(code)
                
                # 基本進場條件 (v4.21)
                if not (rsi < 70 and atr_pct >= 0.5 and ma20 > ma60):
                    continue
                
                entry_price = close
                exit_price = closes[i+holding]
                exit_type = '時間到期'
                exit_day = holding
                
                # 動態出场邏輯
                max_day = exit_config.get('time_max', holding)
                if max_day > len(closes) - i - 1:
                    max_day = len(closes) - i - 1
                
                # 移動停損追蹤
                peak_price = entry_price
                
                for day in range(1, max_day + 1):
                    price = closes[i+day]
                    high_since = max(highs[i:i+day+1])
                    
                    # 更新峰值
                    if exit_config.get('trailing', False):
                        if high_since > peak_price:
                            peak_price = high_since
                    
                    # 1. 停損檢查
                    sl = exit_config.get('stop_loss')
                    if sl:
                        if (price / entry_price - 1) * 100 < -sl:
                            exit_price = price
                            exit_type = '停損'
                            exit_day = day
                            break
                    
                    # 2. 獲利目標
                    pt = exit_config.get('profit_target')
                    if pt:
                        if (price / entry_price - 1) * 100 >= pt:
                            exit_price = price
                            exit_type = '目標'
                            exit_day = day
                            break
                    
                    # 3. ATR 移動止損
                    atr_mult = exit_config.get('atr_mult', 0)
                    if atr_mult > 0:
                        if exit_config.get('trailing', False):
                            stop = peak_price - atr_mult * atr
                        else:
                            stop = entry_price - atr_mult * atr
                        
                        if price <= stop:
                            exit_price = price
                            exit_type = 'ATR止損'
                            exit_day = day
                            break
                    
                    # 4. RSI 鈍化出场
                    rsi_cfg = exit_config.get('rsi_exit')
                    if rsi_cfg and day > 1:
                        rsi_curr = get_rsi(closes[:i+day+1])
                        rsi_prev = get_rsi(closes[:i+day])
                        hi_thresh, lo_thresh = rsi_cfg
                        
                        if rsi_prev >= hi_thresh and rsi_curr < lo_thresh:
                            exit_price = price
                            exit_type = 'RSI鈍化'
                            exit_day = day
                            break
                    
                    # 5. 時間到期
                    if day == max_day:
                        exit_price = price
                        exit_type = '時間到期'
                        exit_day = day
                
                ret = (exit_price / entry_price - 1) * 100
                trades.append({
                    'code': code,
                    'return': ret,
                    'exit_type': exit_type,
                    'exit_day': exit_day,
                    'rsi': rsi
                })
        except:
            continue
    
    return trades

def analyze(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg': 0, 'pf': 0, 'mdd': 0, 'exit_stats': {}}
    
    returns = [t['return'] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    total = len(returns)
    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg = np.mean(returns) if total > 0 else 0
    
    total_win = sum(wins) if wins else 0
    total_loss = abs(sum(losses)) if losses else 0
    pf = total_win / total_loss if total_loss > 0 else 0
    
    sorted_ret = sorted(returns)
    cum, max_dd, peak = 0, 0, 0
    for r in sorted_ret:
        cum += r
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    
    exit_stats = {}
    for t in trades:
        et = t.get('exit_type', 'Unknown')
        exit_stats[et] = exit_stats.get(et, 0) + 1
    
    return {'total': total, 'win_rate': win_rate, 'avg': avg, 'pf': pf, 'mdd': max_dd, 'exit_stats': exit_stats}

def main():
    print('='*60)
    print(' Tina v4.21 動態出场策略 - 迭代優化')
    print('='*60)
    
    # 測試配置
    configs = [
        # 基準
        {'name': 'v0_fix5d', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        
        # ATR 移動停損變化
        {'name': 'vA_atr2', 'atr_mult': 2.0, 'trailing': True, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        {'name': 'vA_atr15', 'atr_mult': 1.5, 'trailing': True, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        {'name': 'vA_atr3', 'atr_mult': 3.0, 'trailing': True, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        {'name': 'vA_atr25_nt', 'atr_mult': 2.5, 'trailing': False, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        
        # 停損選項
        {'name': 'vB_sl3', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': None, 'stop_loss': 3, 'rsi_exit': None},
        {'name': 'vB_sl5', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': None, 'stop_loss': 5, 'rsi_exit': None},
        {'name': 'vB_sl_atr', 'atr_mult': 2.5, 'trailing': True, 'time_max': 5, 'profit_target': None, 'stop_loss': 5, 'rsi_exit': None},
        
        # 獲利目標
        {'name': 'vC_pt3', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': 3, 'stop_loss': None, 'rsi_exit': None},
        {'name': 'vC_pt5', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': 5, 'stop_loss': None, 'rsi_exit': None},
        {'name': 'vC_pt_atr', 'atr_mult': 2.5, 'trailing': True, 'time_max': 5, 'profit_target': 5, 'stop_loss': 3, 'rsi_exit': None},
        
        # RSI 鈍化
        {'name': 'vD_rsi75_70', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': (75, 70)},
        {'name': 'vD_rsi80_75', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': (80, 75)},
        {'name': 'vD_rsi70_65', 'atr_mult': 0, 'trailing': False, 'time_max': 5, 'profit_target': None, 'stop_loss': None, 'rsi_exit': (70, 65)},
        
        # 延長持有
        {'name': 'vE_7d', 'atr_mult': 0, 'trailing': False, 'time_max': 7, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        {'name': 'vE_10d', 'atr_mult': 0, 'trailing': False, 'time_max': 10, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        {'name': 'vE_7d_atr', 'atr_mult': 2.5, 'trailing': True, 'time_max': 7, 'profit_target': None, 'stop_loss': None, 'rsi_exit': None},
        
        # 組合
        {'name': 'vF_combo1', 'atr_mult': 2.0, 'trailing': True, 'time_max': 7, 'profit_target': 5, 'stop_loss': 3, 'rsi_exit': (80, 75)},
        {'name': 'vF_combo2', 'atr_mult': 2.5, 'trailing': True, 'time_max': 5, 'profit_target': 3, 'stop_loss': None, 'rsi_exit': (75, 70)},
    ]
    
    results = []
    
    for cfg in configs:
        name = cfg['name']
        print()
        print(' 測試 ' + name + '...')
        trades = backtest(cfg)
        stats = analyze(trades)
        
        print('    交易: ' + str(stats['total']) + ' | 勝率: ' + str(round(stats['win_rate'],1)) + '%')
        print('    平均: ' + str(round(stats['avg'],2)) + '% | PF: ' + str(round(stats['pf'],2)))
        
        if stats['exit_stats']:
            exits = ', '.join([k + '=' + str(v) for k, v in stats['exit_stats'].items()])
            print('    離開: ' + exits)
        
        results.append({'name': name, 'cfg': cfg, 'stats': stats, 'trades': trades})
    
    print()
    print('='*60)
    print(' 版本比較 (排序)')
    print('='*60)
    print()
    print('%-12s %-8s %-8s %-8s %-8s' % ('版本', '交易次', '勝率', '平均', 'PF'))
    print('-'*50)
    
    results.sort(key=lambda x: (x['stats']['win_rate'], x['stats']['total']), reverse=True)
    
    for r in results:
        s = r['stats']
        print('%-12s %-8d %-8.1f %-8.2f %-8.2f' % (r['name'], s['total'], s['win_rate'], s['avg'], s['pf']))
    
    # 最佳版本
    best = results[0]
    base = next((r for r in results if r['name'] == 'v0_fix5d'), results[0])
    
    print()
    print('='*60)
    print(' 迭代優化结果')
    print('='*60)
    print()
    print('[最佳版本]: ' + best['name'])
    print()
    print('【績效對比 vs 基準 (固定5天)】')
    print(' 勝率: ' + str(round(base['stats']['win_rate'],1)) + '% -> ' + str(round(best['stats']['win_rate'],1)) + '%')
    print(' 交易次: ' + str(base['stats']['total']) + ' -> ' + str(best['stats']['total']))
    print(' 平均報酬: ' + str(round(base['stats']['avg'],2)) + '% -> ' + str(round(best['stats']['avg'],2)) + '%')
    print(' PF: ' + str(round(base['stats']['pf'],2)) + ' -> ' + str(round(best['stats']['pf'],2)))
    
    wr_chg = best['stats']['win_rate'] - base['stats']['win_rate']
    total_chg = best['stats']['total'] - base['stats']['total']
    
    print()
    print('【後續行動】')
    if wr_chg > 2 and total_chg > -300:
        print(' ✅ 接受新策略: ' + best['name'])
        print('    - 勝率提升 ' + str(round(wr_chg,1)) + '%')
        print('    - 交易次變化 ' + str(total_chg))
    elif wr_chg >= 0 and total_chg > -100:
        print(' ⚠️ 勝率持平偏優，考慮採納')
    else:
        print(' ❌ 績效未明顯提升，維持 v4.21 + 固定5天')
    
    # 顯示前3名
    print()
    print('【TOP 3 版本】')
    for i, r in enumerate(results[:3], 1):
        s = r['stats']
        print(' ' + str(i) + '. ' + r['name'] + ': ' + str(round(s['win_rate'],1)) + '% WR, ' + str(s['total']) + '筆')
    
    print()
    print('='*60)
    
    # 儲存
    result_save = {
        'best_version': best['name'],
        'stats': best['stats'],
        'all_results': [(r['name'], r['stats']) for r in results]
    }
    with open('Tina_Quant_System/logs/dynamic_exit_result.json', 'w', encoding='utf-8') as f:
        json.dump(result_save, f, ensure_ascii=False, indent=2)
    print(' 已儲存: logs/dynamic_exit_result.json')

if __name__ == '__main__':
    main()