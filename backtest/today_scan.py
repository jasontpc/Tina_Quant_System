# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412']

BLACKLIST = ['2615','1590','2382','2317','2303','3008','3231','2408','3443','6446','6669','2597']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:50]

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

print('='*80)
print(' 台股 (2026-04-22) 市值前50 - 技術面篩選')
print('='*80)

results = []
for code in STOCKS:
    try:
        h = yf.Ticker(code+'.TW').history(period='65d')
        if len(h) < 61: continue
        cl = list(h['Close'])
        vol = list(h['Volume'])
        
        rs = rsi(cl)
        ma20 = np.mean(cl[-20:])
        ma60 = np.mean(cl[-60:])
        price = cl[-1]
        bias = (price / ma20 - 1) * 100
        
        # ATR
        trs = []
        for i in range(-14, 0):
            hi = h['High'].iloc[i]
            lo = h['Low'].iloc[i]
            cl_prev = h['Close'].iloc[i-1] if i > -len(h)+1 else h['Close'].iloc[i]
            trs.append(max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev)))
        atr = np.mean(trs) if trs else 30
        atr_pct = (atr / price) * 100
        
        # 漲跌
        change = (cl[-1] / cl[-2] - 1) * 100 if len(cl) > 1 else 0
        
        results.append({
            'code': code, 'price': price, 'change': change,
            'rs': rs, 'ma20': ma20, 'ma60': ma60, 'bias': bias,
            'atr_pct': atr_pct
        })
    except:
        pass

# Sort by RSI (oversold first)
results.sort(key=lambda x: x['rs'])

print('\n技術面數據 (按 RSI 排序):')
print('-'*80)
print('代碼   價格     漲跌%    RSI    MA20偏離%  ATR%   MA20>MA60')
print('-'*80)
for r in results[:25]:
    ma_check = 'Y' if r['ma20'] > r['ma60'] else 'N'
    print('%5s %8.2f %+7.2f%% %5.1f  %+8.2f%%  %5.2f%%   %s' % (
        r['code'], r['price'], r['change'], r['rs'], r['bias'], r['atr_pct'], ma_check))

print()
print('-'*80)
print('共 %d 檔資料' % len(results))
print('='*80)
print('\nv4.21 進場條件: RSI<70, ATR>=0.5%, MA20>MA60, 站上MA20')
print('='*80)