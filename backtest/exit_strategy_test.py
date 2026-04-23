# -*- coding: utf-8 -*-
"""
Tina v4.21 出場策略實驗
A. ATR 吊燈止損
B. 時間效率過濾
C. RSI 高檔鈍化出場
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

def backtest_exit(version_name, holding=5):
    trades = []
    
    for code in STOCKS:
        try:
            h = yf.Ticker(code + '.TW').history(period='200d')
            if len(h) < 120:
                continue
            
            closes = list(h['Close'].values)
            highs = list(h['High'].values)
            
            for i in range(60, len(closes) - holding - 20):
                close = closes[i]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                
                f_net, t_net = get_inst(code)
                
                # 基本進場條件 (v4.21)
                if not (rsi < 70 and atr_pct >= 0.5 and ma20 > ma60):
                    continue
                
                entry_price = close
                exit_price = closes[i+holding]
                exit_type = '固定5天'
                exit_day = holding
                
                if version_name == 'vA_atr_stop':
                    # ATR 吊燈止損
                    for day in range(1, holding + 1):
                        price = closes[i+day]
                        high_since = max(highs[i:i+day+1])
                        stop = high_since - 2.5 * atr
                        
                        if price <= stop:
                            exit_price = price
                            exit_type = 'ATR止損'
                            exit_day = day
                            break
                
                elif version_name == 'vB_time_eff':
                    # 時間效率 - 5天未獲利>1%則強平
                    for day in range(1, holding + 1):
                        price = closes[i+day]
                        profit_pct = (price / entry_price - 1) * 100
                        
                        if profit_pct < -1:
                            exit_price = price
                            exit_type = '時間止損'
                            exit_day = day
                            break
                
                elif version_name == 'vC_rsi_exit':
                    # RSI 高檔鈍化出场
                    rsi_entry = rsi
                    for day in range(1, holding + 1):
                        price = closes[i+day]
                        rsi_current = get_rsi(closes[:i+day+1])
                        
                        if rsi_entry > 80 and rsi_current < 75:
                            exit_price = price
                            exit_type = 'RSI鈍化'
                            exit_day = day
                            break
                
                elif version_name == 'vD_combo':
                    # ATR + RSI 組合
                    for day in range(1, holding + 1):
                        price = closes[i+day]
                        high_since = max(highs[i:i+day+1])
                        
                        stop = high_since - 2.5 * atr
                        if price <= stop:
                            exit_price = price
                            exit_type = 'ATR止損'
                            exit_day = day
                            break
                        
                        rsi_current = get_rsi(closes[:i+day+1])
                        if rsi > 80 and rsi_current < 75:
                            exit_price = price
                            exit_type = 'RSI鈍化'
                            exit_day = day
                            break
                
                # v0 是基準，只有else分支，維持固定5天
                
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

def analyze_trades(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg': 0, 'pf': 0, 'mdd': 0, 'exit_stats': {}}
    
    returns = [t['return'] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    total = len(returns)
    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg = np.mean(returns) if total > 0 else 0
    
    total_win = sum(wins)
    total_loss = abs(sum(losses))
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
    print(' Tina v4.21 出場策略實驗')
    print('='*60)
    
    versions = [
        ('v0_fix5d', '基準 (固定5天)'),
        ('vA_atr_stop', 'A. ATR吊燈止損'),
        ('vB_time_eff', 'B. 時間效率過濾'),
        ('vC_rsi_exit', 'C. RSI高檔鈍化'),
        ('vD_combo', 'D. ATR+RSI組合'),
    ]
    
    results = []
    
    for name, desc in versions:
        print()
        print(' 測試 ' + name + ' (' + desc + ')...')
        trades = backtest_exit(name, 5)
        stats = analyze_trades(trades)
        
        print('    交易: ' + str(stats['total']) + ' | 勝率: ' + str(round(stats['win_rate'],1)) + '%')
        print('    平均: ' + str(round(stats['avg'],2)) + '% | PF: ' + str(round(stats['pf'],2)))
        print('    MDD: ' + str(round(stats['mdd'],2)) + '%')
        
        if stats['exit_stats']:
            exits = ', '.join([k + '=' + str(v) for k, v in stats['exit_stats'].items()])
            print('    離開: ' + exits)
        
        results.append({'name': name, 'desc': desc, 'stats': stats, 'trades': trades})
    
    print()
    print('='*60)
    print(' 版本比較')
    print('='*60)
    print()
    print('%-12s %-20s %-8s %-8s %-8s %-8s' % ('版本', '說明', '交易次', '勝率', '平均', 'PF'))
    print('-'*70)
    
    results.sort(key=lambda x: (x['stats']['win_rate'], x['stats']['total']), reverse=True)
    
    for r in results:
        s = r['stats']
        print('%-12s %-20s %-8d %-8.1f %-8.2f %-8.2f' % (
            r['name'], r['desc'], s['total'], s['win_rate'], s['avg'], s['pf']))
    
    best = results[0]
    base = next((r for r in results if r['name'] == 'v0_fix5d'), results[0])
    
    print()
    print('='*60)
    print(' 策略控制决策')
    print('='*60)
    print()
    print('[最佳版本]: ' + best['name'] + ' (' + best['desc'] + ')')
    print()
    print('【績效對比 vs 基準 (固定5天)】')
    print(' 勝率: ' + str(round(base['stats']['win_rate'],1)) + '% -> ' + str(round(best['stats']['win_rate'],1)) + '%')
    print(' 交易次: ' + str(base['stats']['total']) + ' -> ' + str(best['stats']['total']))
    print(' 平均報酬: ' + str(round(base['stats']['avg'],2)) + '% -> ' + str(round(best['stats']['avg'],2)) + '%')
    print(' PF: ' + str(round(base['stats']['pf'],2)) + ' -> ' + str(round(best['stats']['pf'],2)))
    print(' MDD: ' + str(round(base['stats']['mdd'],2)) + '% -> ' + str(round(best['stats']['mdd'],2)) + '%')
    
    print()
    print('【離場類型統計】')
    for r in results:
        if r['stats']['exit_stats']:
            print(' ' + r['name'] + ': ' + ', '.join([k + '=' + str(v) for k, v in r['stats']['exit_stats'].items()]))
    
    print()
    print('【後續行動】')
    wr_chg = best['stats']['win_rate'] - base['stats']['win_rate']
    
    if wr_chg > 2:
        print(' ✅ 接受新策略: ' + best['name'])
    elif wr_chg >= -1:
        print(' ⚠️ 勝率持平，維持固定5天')
    else:
        print(' ❌ 績效劣化，維持固定5天')
    
    print()
    print('='*60)
    
    result_save = {
        'best_version': best['name'],
        'desc': best['desc'],
        'stats': best['stats'],
        'all_results': [(r['name'], r['desc'], r['stats']) for r in results]
    }
    with open('Tina_Quant_System/logs/exit_strategy.json', 'w', encoding='utf-8') as f:
        json.dump(result_save, f, ensure_ascii=False, indent=2)
    print(' 已儲存: logs/exit_strategy.json')

if __name__ == '__main__':
    main()