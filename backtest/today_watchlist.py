# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
import pandas as pd

DB = 'skills/stock-analyzer/scripts/tina_master.db'

STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393']

BLACKLIST = ['2615','1590','2382','2317','2303','3008','3231','2408','3443','6446','6669','2597']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:50]

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
print(' 台股 Top50 今日開盤觀察名單 (2026-04-23)')
print(' v4.21 進場條件篩選')
print('='*80)

signals = []
for code in STOCKS:
    try:
        h = yf.Ticker(code+'.TW').history(period='65d')
        if len(h) < 60: continue
        cl = list(h['Close'])
        vol = list(h['Volume'])
        
        rs = rsi(cl)
        ma20 = np.mean(cl[-20:])
        ma60 = np.mean(cl[-60:]) if len(cl) >= 60 else ma20
        atr = calc_atr(h)
        atr_pct = atr / cl[-1] * 100
        bias = (cl[-1] / ma20 - 1) * 100
        price = cl[-1]
        vr = vol[-1] / np.mean(vol[-20:]) if np.mean(vol[-20:]) > 0 else 0
        
        # v4.21 技術面篩選
        if rs >= 70: continue
        if cl[-1] < ma20: continue
        if ma20 <= ma60: continue
        if atr_pct < 0.5: continue
        
        # 法人篩選
        f_days = t_days = 0
        for dd in range(1, 4):
            dt = (pd.to_datetime('2026-04-22') - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
            if dt in inst_raw.get(code, {}):
                if inst_raw[code][dt][0] > 0: f_days += 1
                if inst_raw[code][dt][1] > 0: t_days += 1
        
        inst_ok = max(f_days, t_days) >= 1
        
        signals.append({
            'code': code, 'price': price, 'rs': rs,
            'ma20': ma20, 'ma60': ma60, 'bias': bias,
            'atr': atr_pct, 'vr': vr, 'inst_ok': inst_ok,
            'f_days': f_days, 't_days': t_days
        })
    except:
        pass

# Sort by RSI then by bias
signals.sort(key=lambda x: (x['rs'], x['bias']))

print('\n技術面篩選結果:')
print('-'*80)
print('代碼   價格      RSI   ATR%   Bias%   MA20>MA60  法人')
print('-'*80)
for s in signals:
    ma_check = 'Y' if s['ma20'] > s['ma60'] else 'N'
    inst = '✅' if s['inst_ok'] else '❌'
    print('%5s %8.2f %5.1f %6.2f%% %+7.2f%%    %s       %s' % (
        s['code'], s['price'], s['rs'], s['atr'], s['bias'], ma_check, inst))

print()
print('='*80)
print(' 符合 v4.21 進場條件: %d 檔' % len(signals))
print('='*80)

# Filter inst confirmed
inst_confirmed = [s for s in signals if s['inst_ok']]
print('\n法人確認可以進場: %d 檔' % len(inst_confirmed))
for s in inst_confirmed[:10]:
    print('  %s - RSI %.1f, Bias %+.2f%%' % (s['code'], s['rs'], s['bias']))

print()
print('='*80)