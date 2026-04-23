# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

print('='*75)
print(' 台股交易量前10名技術分析 (2026-04-23)')
print('='*75)

# Top 10 volume stocks
stocks = [
    ('2317', '鴻海', 135835479, 221.0),
    ('1303', '南亞', 59039088, 89.4),
    ('2313', '華南金', 50561222, 247.0),
    ('2891', '中信金', 36184653, 53.5),
    ('2882', '兆豐金', 32027678, 75.9),
    ('2002', '台泥', 31266758, 19.55),
    ('2883', '開發金', 26515992, 20.8),
    ('2330', '台積電', 24762881, 2050.0),
    ('2881', '富邦金', 23316872, 88.3),
    ('2454', '聯發科', 23044579, 2295.0),
]

print()
print('%-4s %-6s %-8s %10s %5s %7s %6s  %s' % ('排行', '代碼', '名稱', '成交量', 'RSI', 'Bias%', 'ATR%', '評估'))
print('-'*75)

for i, (code, name, vol, price) in enumerate(stocks, 1):
    try:
        h = yf.Ticker(code+'.TW').history(period='65d')
        if len(h) < 60:
            print('%-4d %-6s %-8s %10d --不及60天--' % (i, code, name, vol))
            continue
        
        close = float(h['Close'].iloc[-1])
        prev = float(h['Close'].iloc[-2])
        change = (close / prev - 1) * 100
        
        cl = list(h['Close'])
        ma20 = np.mean(cl[-20:])
        ma60 = np.mean(cl[-60:])
        bias = (close / ma20 - 1) * 100
        
        d = np.diff(cl)
        g = np.where(d > 0, d, 0)
        l = np.where(d > 0, 0, -d)
        ag = np.mean(g[-14:])
        al = np.mean(l[-14:])
        rs = 100 - (100 / (1 + ag / al)) if al != 0 else 50
        
        trs = []
        for j in range(-15, 0):
            hi = float(h['High'].iloc[j])
            lo = float(h['Low'].iloc[j])
            cl_p = float(h['Close'].iloc[j-1])
            trs.append(max(hi-lo, abs(hi-cl_p), abs(lo-cl_p)))
        atr = np.mean(trs)
        atr_pct = atr / close * 100
        
        # v4.21 check
        v421_ok = rs < 70 and abs(bias) < 10 and ma20 > ma60 and atr_pct >= 0.5
        
        # RSI icon
        if rs >= 85:
            rs_icon = '🔴'
        elif rs >= 70:
            rs_icon = '🟠'
        elif rs >= 60:
            rs_icon = '🟡'
        else:
            rs_icon = '🟢'
        
        # Status
        if v421_ok:
            status = '✅ 可進場'
        elif rs >= 70:
            status = '⚠️ RSI高'
        elif abs(bias) >= 10:
            status = '⚠️ 偏離大'
        elif ma20 <= ma60:
            status = '⚠️ 空頭'
        else:
            status = '🟡 待觀察'
        
        arrow = '↑' if change > 0 else '↓'
        print('%-4d %-6s %-8s %10d %s%.1f %+6.2f%% %5.2f%%  %s (%s%.2f%%)' % (
            i, code, name, vol, rs_icon, rs, bias, atr_pct, status, arrow, change))
        
    except Exception as e:
        print('%-4d %-6s %-8s %10d ERROR: %s' % (i, code, name, vol, e))

print()
print('='*75)
print(' RSI 熱度: 🔴85+ 🟠70-84 🟡60-69 🟢50-59')
print(' v4.21: RSI<70 + Bias<10% + MA20>MA60 + ATR>=0.5%')
print('='*75)