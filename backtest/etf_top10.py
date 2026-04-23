# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

# 台股ETF市值前10 (預估)
ETFS = [
    ('0050', '元大台灣50'),
    ('00631L', '元大台灣50正2'),
    ('00881', '國泰台灣5G+'),
    ('00891', '中信關鍵半導體'),
    ('00757', '統一FANG+'),
    ('00662', '富邦NASDAQ100'),
    ('0056', '元大高股息'),
    ('00830', '富邦NASDAQ'),
    ('00713', '元大台灣高息低波'),
    ('00927', '永豐優息存股'),
]

print('='*75)
print(' 台股ETF市值前10 - 今日盤勢 (2026-04-23)')
print('='*75)

results = []
for code, name in ETFS:
    try:
        h = yf.Ticker(code + '.TW').history(period='10d')
        if len(h) < 2:
            continue
        
        prices = list(h['Close'])
        current = float(prices[-1])
        prev = float(prices[-2])
        change = (current / prev - 1) * 100
        
        cl = list(h['Close'])
        ma5 = np.mean(cl[-5:]) if len(cl) >= 5 else current
        ma20 = np.mean(cl[-20:]) if len(cl) >= 20 else current
        
        # RSI
        d = np.diff(cl)
        g = np.where(d > 0, d, 0)
        l = np.where(d > 0, 0, -d)
        ag = np.mean(g[-14:])
        al = np.mean(l[-14:])
        rs = 100 - (100 / (1 + ag / al)) if al != 0 else 50
        
        # Volume
        vol = list(h['Volume'])
        vr = vol[-1] / np.mean(vol[-5:]) if np.mean(vol[-5:]) > 0 else 0
        
        # ATR %
        trs = []
        for i in range(-5, 0):
            if i >= -len(h):
                hi = float(h['High'].iloc[i])
                lo = float(h['Low'].iloc[i])
                cl_p = float(h['Close'].iloc[i-1]) if i-1 >= 0 else current
                trs.append(max(hi-lo, abs(hi-cl_p), abs(lo-cl_p)))
        atr = np.mean(trs) if trs else 0
        atr_pct = atr / current * 100
        
        results.append({
            'code': code, 'name': name,
            'price': current, 'change': change,
            'ma5': ma5, 'ma20': ma20,
            'rs': rs, 'vr': vr, 'atr': atr_pct
        })
    except Exception as e:
        pass

# Sort by volume
results.sort(key=lambda x: x['vr'], reverse=True)

print()
print('%-6s %-12s %8s %6s %5s %5s %6s  %s' % ('代碼', '名稱', '價格', '漲跌', 'RSI', 'VR', 'ATR%', '評估'))
print('-'*75)

for r in results:
    arrow = '↑' if r['change'] > 0 else '↓'
    
    # RSI icon
    if r['rs'] >= 85:
        rs_icon = '🔴'
    elif r['rs'] >= 70:
        rs_icon = '🟠'
    elif r['rs'] >= 50:
        rs_icon = '🟡'
    else:
        rs_icon = '🟢'
    
    # Trend based on price vs MA5
    if r['price'] > r['ma5']:
        trend = '↗'
    else:
        trend = '↘'
    
    # Assess
    if r['change'] > 2:
        assess = '🔥 強漲'
    elif r['change'] > 0:
        assess = '↑ 上漲'
    elif r['change'] < -2:
        assess = '🔻 暴跌'
    else:
        assess = '↓ 下跌'
    
    print('%-6s %-12s %8.2f %s%.2f%% %s%.1f %5.2f %5.2f%%  %s' % (
        r['code'], r['name'], r['price'], arrow, r['change'],
        rs_icon, r['rs'], r['vr'], r['atr'], assess))

print()
print('='*75)
print(' RSI: 🔴85+ 🟠70-84 🟡50-69 🟢<50')
print(' VR: >1.5=放量 >1.0=平量 <0.8=縮量')
print('='*75)