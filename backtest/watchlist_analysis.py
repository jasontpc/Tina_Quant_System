# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import pandas as pd

DB = 'skills/stock-analyzer/scripts/tina_master.db'
STOCKS = ['2891', '2231', '1326', '2353', '1301', '2385']

conn = sqlite3.connect(DB)
cur = conn.cursor()
inst_raw = {}
for code in STOCKS:
    cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', (code,))
    inst_raw[code] = {}
    for date, f, t in cur.fetchall():
        inst_raw[code][date] = (f or 0, t or 0)
conn.close()

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr(h):
    trs = []
    for i in range(-14, 0):
        hi = h['High'].iloc[i]
        lo = h['Low'].iloc[i]
        cl_prev = h['Close'].iloc[i-1]
        trs.append(max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev)))
    return np.mean(trs)

print('='*80)
print(' 觀察名單 v4.21 分析 (2026-04-22)')
print('='*80)

results = []
for code in STOCKS:
    try:
        h = yf.Ticker(code+'.TW').history(period='60d')
        if len(h) < 60: continue
        cl = list(h['Close'])
        
        rs = rsi(cl)
        ma20 = np.mean(cl[-20:])
        ma60 = np.mean(cl[-60:]) if len(cl) >= 60 else ma20
        atr = calc_atr(h)
        atr_pct = atr / cl[-1] * 100
        bias = (cl[-1] / ma20 - 1) * 100
        price = cl[-1]
        
        # 法人
        f_days = t_days = 0
        for dd in range(1, 4):
            dt = (pd.to_datetime('2026-04-22') - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
            if dt in inst_raw.get(code, {}):
                if inst_raw[code][dt][0] > 0: f_days += 1
                if inst_raw[code][dt][1] > 0: t_days += 1
        
        inst_ok = max(f_days, t_days) >= 1
        
        results.append({
            'code': code, 'price': price, 'rs': rs,
            'ma20': ma20, 'ma60': ma60, 'bias': bias,
            'atr': atr_pct, 'inst_ok': inst_ok
        })
    except:
        pass

print()
print('代碼   價格      RSI   ATR%   Bias%   MA20>MA60  法人')
print('-'*80)
for r in results:
    ma_check = 'Y' if r['ma20'] > r['ma60'] else 'N'
    inst = '✅' if r['inst_ok'] else '❌'
    print('%5s %8.2f %5.1f %6.2f%% %+7.2f%%    %s       %s' % (
        r['code'], r['price'], r['rs'], r['atr'], r['bias'], ma_check, inst))

print()
print('='*80)
print(' ✅ = 滿足進場條件 | ❌ = 不滿足')
print('='*80)