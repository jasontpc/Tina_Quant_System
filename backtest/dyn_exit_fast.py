# -*- coding: utf-8 -*-
"""
Tina v4.21 動態出场 - 極速版
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import json

STOCKS = ['2330','2454','2317','3034','2451','2881','2891','3008','3189','6415','8046','2385']

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def bt(name, holding, stop_mult=0, trailing=False, max_d=None, profit_t=None, stop_l=None, rsi_th=None):
    trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code + '.TW').history(period='180d')
            if len(h) < 100:
                continue
            closes = list(h['Close'].values)
            highs = list(h['High'].values)
            
            for i in range(50, len(closes) - holding - 15):
                close = closes[i]
                ma20 = np.mean(closes[i-19:i+1])
                rsi = get_rsi(closes[:i+1])
                
                if rsi >= 70 or ma20 <= closes[i]:
                    continue
                
                entry = close
                peak = entry
                exit_price = closes[i+holding]
                exit_type = '時間'
                exit_day = holding
                
                mx = max_d if max_d else holding
                
                for day in range(1, mx + 1):
                    price = closes[i+day]
                    high = max(highs[i:i+day+1])
                    
                    if trailing and high > peak:
                        peak = high
                    
                    # Stop loss
                    if stop_l and (price / entry - 1) * 100 < -stop_l:
                        exit_price = price
                        exit_type = '停損'
                        exit_day = day
                        break
                    
                    # ATR trailing stop
                    if stop_mult > 0:
                        stop = (peak if trailing else entry) - stop_mult * (high - closes[i])
                        if price <= stop:
                            exit_price = price
                            exit_type = 'ATR'
                            exit_day = day
                            break
                    
                    # Profit target
                    if profit_t and (price / entry - 1) * 100 >= profit_t:
                        exit_price = price
                        exit_type = '目標'
                        exit_day = day
                        break
                    
                    # RSI exit
                    if rsi_th and day > 1:
                        rsi_c = get_rsi(closes[:i+day+1])
                        rsi_p = get_rsi(closes[:i+day])
                        if rsi_p >= rsi_th[0] and rsi_c < rsi_th[1]:
                            exit_price = price
                            exit_type = 'RSI'
                            exit_day = day
                            break
                    
                    if day == mx:
                        exit_price = price
                        exit_type = '時間'
                
                ret = (exit_price / entry - 1) * 100
                trades.append({'code': code, 'return': ret, 'exit': exit_type, 'day': exit_day})
        except:
            continue
    return trades

def st(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'avg': 0, 'pf': 0}
    rets = [t['return'] for t in trades]
    wins = [r for r in rets if r > 0]
    total = len(rets)
    wr = len(wins) / total * 100 if total > 0 else 0
    avg = np.mean(rets) if total > 0 else 0
    pf = abs(sum(wins) / abs(sum([r for r in rets if r <= 0]))) if wins and [r for r in rets if r <= 0] else 0
    exit_s = {}
    for t in trades:
        exit_s[t['exit']] = exit_s.get(t['exit'], 0) + 1
    return {'total': total, 'win_rate': wr, 'avg': avg, 'pf': pf, 'exits': exit_s}

print('='*60)
print(' Tina v4.21 動態出场 - 極速版')
print('='*60)

configs = [
    ('v0_5d', 5, 0, False, None, None, None, None),
    ('vA_atr2', 5, 2.0, True, None, None, None, None),
    ('vA_atr25', 5, 2.5, True, None, None, None, None),
    ('vB_sl3', 5, 0, False, None, None, 3, None),
    ('vB_sl5', 5, 0, False, None, None, 5, None),
    ('vC_pt3', 5, 0, False, None, 3, None, None),
    ('vC_pt5', 5, 0, False, None, 5, None, None),
    ('vD_rsi75', 5, 0, False, None, None, None, (75, 70)),
    ('vE_7d', 7, 0, False, None, None, None, None),
    ('vE_10d', 10, 0, False, None, None, None, None),
    ('vF_combo', 7, 2.0, True, None, 5, 3, (80, 75)),
]

results = []
for cfg in configs:
    name, hold, sm, tr, md, pt, sl, rt = cfg
    print(' ' + name + '...')
    trades = bt(name, hold, sm, tr, md, pt, sl, rt)
    s = st(trades)
    print('   ' + str(s['total']) + '筆 ' + str(round(s['win_rate'],1)) + '% WR ' + str(round(s['avg'],2)) + '% avg')
    if s['exits']:
        print('   離開: ' + str(s['exits']))
    results.append((name, s, cfg))

print()
print('='*60)
print(' 版本比較')
print('='*60)
print()
print('%-10s %-8s %-8s %-8s %-8s' % ('版本', '交易', '勝率', '平均', 'PF'))
print('-'*40)

results.sort(key=lambda x: (x[1]['win_rate'], x[1]['total']), reverse=True)

for r in results:
    s = r[1]
    print('%-10s %-8d %-8.1f %-8.2f %-8.2f' % (r[0], s['total'], s['win_rate'], s['avg'], s['pf']))

best = results[0]
base = next((r for r in results if r[0] == 'v0_5d'), results[0])

print()
print('='*60)
print('[最佳]: ' + best[0])
print('[勝率]: ' + str(round(base[1]['win_rate'],1)) + '% -> ' + str(round(best[1]['win_rate'],1)) + '%')
print('[交易]: ' + str(base[1]['total']) + ' -> ' + str(best[1]['total']))
print()

if best[1]['win_rate'] > base[1]['win_rate']:
    print(' ✅ 更新版本')
else:
    print(' ❌ 維持 v0_5d (固定5天)')

print()
print('='*60)

with open('Tina_Quant_System/logs/dynamic_exit.json', 'w', encoding='utf-8') as f:
    json.dump({'best': best[0], 'stats': best[1]}, f, ensure_ascii=False)