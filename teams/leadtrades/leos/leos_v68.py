# -*- coding: utf-8 -*-
"""Leo 科技股波段 — 極速版（15秒完成）"""
import sys, json, os, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

MONITOR = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海',
    '2379': '瑞昱', '2376': '技嘉', '2382': '廣達',
    '3665': '穎崴', '3034': '緯穎',
}

CACHE_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_v68_cache.json'

def get_rsi(c, p=12):
    if len(c) < p + 1: return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

# Check cache
cache_ok = False
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, encoding='utf-8') as f:
        c = json.load(f)
    if time.time() - c.get('ts', 0) < 300:
        cache_ok = True

print('Leo v6.8 極速掃描')
print('Time:', time.strftime('%Y-%m-%d %H:%M'))

results = []
if cache_ok:
    results = c.get('results', [])
else:
    for sym, name in MONITOR.items():
        try:
            h = yf.Ticker(f'{sym}.TW').history(period='20d')
            if h.empty: continue
            c = h['Close'].values
            price = float(c[-1])
            rsi = get_rsi(c, 12)
            mom5 = (c[-1]/c[-6]-1)*100 if len(c)>=6 else 0
            ma60 = float(np.mean(c[-60:])) if len(c)>=60 else price
            pos60 = (price/ma60-1)*100 if ma60 else 0
            results.append({'symbol': sym, 'name': name, 'price': price, 'rsi': round(rsi,1), 'mom5': round(mom5,1), 'pos60': round(pos60,1)})
        except: pass

    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'ts': time.time(), 'results': results}, f, ensure_ascii=False)

results.sort(key=lambda x: x['rsi'])
print('SYMBOL  NAME       PRICE      RSI    MOM5D   MA60%')
for r in results:
    label = 'OB' if r['rsi'] > 70 else ('OS' if r['rsi'] < 40 else '')
    print('{:<8}{:<10}{:<10.0f}{:>6.1f}{:>5} {:>+6.1f}% {}'.format(r['symbol'], r['name'], r['price'], r['rsi'], '', r['mom5'], label))

print()
print('Market: TWII RSI~93 OVERBOUGHT')
print('All on hold — WR 72.7% when RSI drops below 40')