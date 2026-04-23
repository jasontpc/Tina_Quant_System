# -*- coding: utf-8 -*-
"""
Tina v4.21 極速迭代 - 精簡版
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

STOCKS = ['2330','2454','2317','3034','2379','2451','2881','2882','2891','3008','3189','3231','3665','6415','8046','2385']

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def bt(rsi_max, ma_req, holding=5):
    trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code + '.TW').history(period='150d')
            if len(h) < 100:
                continue
            closes = list(h['Close'].values)
            for i in range(50, len(closes) - holding - 20):
                close = closes[i]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                rsi = get_rsi(closes[:i+1])
                
                ok = rsi < rsi_max
                if ma_req:
                    ok = ok and ma20 > ma60
                
                if ok:
                    ret = (closes[i+holding] / close - 1) * 100
                    trades.append(ret)
        except:
            continue
    return trades

def st(trades):
    if not trades:
        return 0, 0, 0, 0
    wins = [t for t in trades if t > 0]
    total = len(trades)
    wr = len(wins) / total * 100 if total > 0 else 0
    avg = np.mean(trades) if total > 0 else 0
    pf = abs(sum(wins) / abs(sum([t for t in trades if t <= 0]))) if wins and [t for t in trades if t <= 0] else 0
    return total, wr, avg, pf

print('='*60)
print(' Tina v4.21 極速迭代')
print('='*60)

configs = [
    ('v1', 70, False, '基準 v4.21'),
    ('v2', 65, False, 'RSI<65'),
    ('v3', 60, False, 'RSI<60'),
    ('v4', 70, True, 'MA20>MA60'),
    ('v5', 65, True, 'RSI<65+MA'),
]

results = []
for name, rsi_max, ma_req, desc in configs:
    trades = bt(rsi_max, ma_req)
    total, wr, avg, pf = st(trades)
    results.append((name, desc, total, wr, avg, pf))
    print(name + ' ' + desc + ': ' + str(total) + '筆 ' + str(round(wr,1)) + '%')

print()
print('='*60)
results.sort(key=lambda x: (x[3], x[2]), reverse=True)
for r in results:
    print(r[0] + ': ' + r[1] + ' -> ' + str(round(r[3],1)) + '% WR, ' + str(r[2]) + '筆')

best = results[0]
base = results[0]
print()
print('【最佳版本】: ' + best[0])
print('【說明】: ' + best[1])
print()
print(' 勝率: ' + str(round(base[3],1)) + '% -> ' + str(round(best[3],1)) + '%')
print(' 交易次: ' + str(base[2]) + ' -> ' + str(best[2]))
print()
print('【後續行動】: ' + ('更新' if best[3] > base[3] else '維持 v4.21'))
print('='*60)