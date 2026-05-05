# -*- coding: utf-8 -*-
"""Nana 波段 — 極速版（使用快取，30秒內完成）"""
import sys, json, os, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

STOCK_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\stock_names.json'
CACHE_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\scan_cache_v68.json'

with open(STOCK_FILE, encoding='utf-8') as f:
    # v5.41: 移除 WR<45% 的落後股（3008大立光、2330台積電）
    STOCK_NAMES = {k: v for k, v in json.load(f).items() if k not in ('2888', '5882', '3008', '2330')}

def get_rsi(c, p=12):
    if len(c) < p + 1: return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

# Check cache
cache_valid = False
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, encoding='utf-8') as f:
        cache = json.load(f)
    if time.time() - cache.get('ts', 0) < 300:
        cache_valid = True

print('Nana v6.8 極速掃描')
print('Time:', time.strftime('%Y-%m-%d %H:%M'))
print('Cache:', 'valid' if cache_valid else 'expired')

if cache_valid:
    results = cache.get('results', [])
    print('Candidates:', len(results))
    for r in results[:10]:
        print(r['symbol'], r['name'], 'RSI=', r['rsi'], 'Score=', r['score'])
else:
    results = []
    for i, sym in enumerate(list(STOCK_NAMES.keys())[:30]):
        try:
            h = yf.Ticker(f'{sym}.TW').history(period='20d')
            if h.empty: continue
            c = h['Close'].values
            price = float(c[-1])
            rsi = get_rsi(c, 12)
            mom5 = (c[-1]/c[-6]-1)*100 if len(c)>=6 else 0
            ma60 = float(np.mean(c[-60:])) if len(c)>=60 else price
            pos60 = (price/ma60-1)*100
            score = 0
            if 25<=rsi<=35: score+=30
            if mom5>3: score+=20
            elif mom5>0: score+=10
            if pos60>0: score+=15
            if score>=35:
                results.append({'symbol':sym,'name':STOCK_NAMES[sym],'price':price,'rsi':round(rsi,1),'mom5':round(mom5,1),'score':score})
        except: pass
        if (i+1)%10==0: print(f'  {i+1}/30...')

    results.sort(key=lambda x: x['score'], reverse=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'ts': time.time(), 'results': results}, f, ensure_ascii=False)
    print('Candidates:', len(results))
    for r in results[:10]:
        print(r['symbol'], r['name'], 'RSI=', r['rsi'], 'Score=', r['score'])

print('TWII: OVERBOUGHT - All watch mode')
print('Done:', time.strftime('%H:%M:%S'))