# -*- coding: utf-8 -*-
"""
Nana v2.0 - 快速測試版
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import json

STOCKS = ['2330', '2454', '2317', '3034', '2451', '2881', '2891', '6415', '8046']

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def bt_test():
    """簡化回測測試"""
    print('='*60)
    print(' Nana v2.0 快速測試')
    print('='*60)
    
    # 參數測試
    params = {
        'rsi_low': 40,
        'rsi_high': 70,
        'atr_min': 0.3,
        'inst_max': 80,
        'entry_threshold': 60
    }
    
    results = []
    
    for code in STOCKS:
        try:
            h = yf.Ticker(code + '.TW').history(period='180d')
            if len(h) < 60:
                continue
            
            closes = list(h['Close'].values)
            
            for i in range(30, len(closes) - 10):
                close = closes[i]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                rsi = get_rsi(closes[:i+1])
                
                hi = float(h['High'].iloc[i])
                lo = float(h['Low'].iloc[i])
                cl_prev = float(h['Close'].iloc[i-1])
                atr = max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev))
                atr_pct = atr / close * 100
                
                # 進場條件
                if not (params['rsi_low'] <= rsi <= params['rsi_high']):
                    continue
                if atr_pct < params['atr_min']:
                    continue
                if not (ma20 > ma60):
                    continue
                
                # 假設法人 > 0 (簡化)
                f_net = 1000  # 假設買超
                
                # 評分
                score = 0
                if f_net > 0:
                    score += 40
                if params['rsi_low'] <= rsi <= params['rsi_high']:
                    score += 10
                if ma20 > ma60:
                    score += 5
                if atr_pct >= 0.3:
                    score += 5
                
                if score < params['entry_threshold']:
                    continue
                
                # 持有5天後出场
                exit_price = closes[i+5]
                ret = (exit_price / close - 1) * 100
                
                results.append({
                    'code': code,
                    'date_idx': i,
                    'entry': close,
                    'exit': exit_price,
                    'return': ret,
                    'score': score
                })
        
        except Exception as e:
            print(f'  {code} 錯誤: {e}')
            continue
    
    return results

# 測試
trades = bt_test()

print()
print('測試結果: ' + str(len(trades)) + ' 筆交易')
print()

if trades:
    rets = [t['return'] for t in trades]
    wins = [r for r in rets if r > 0]
    
    print('勝率: ' + str(round(len(wins)/len(rets)*100, 1)) + '%')
    print('平均報酬: ' + str(round(np.mean(rets), 2)) + '%')
    
    # 顯示前5筆
    trades.sort(key=lambda x: x['return'], reverse=True)
    print()
    print('TOP 5:')
    for t in trades[:5]:
        icon = '▲' if t['return'] > 0 else '▼'
        print(f"  {t['code']} {t['entry']:.0f} -> {t['exit']:.0f} {icon}{abs(t['return']):.1f}%")

print()
print('='*60)
print(' 快速測試完成')
print('='*60)

# 儲存結果
with open('Tina_Quant_System/teams/nana/test_result.json', 'w', encoding='utf-8') as f:
    json.dump({'total_trades': len(trades)}, f, ensure_ascii=False)