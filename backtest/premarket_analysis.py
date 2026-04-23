# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

STOCKS = [('2891', '中信金'), ('2385', '精英'), ('2353', '兆赫')]

print('='*70)
print(' 盤前分析 (2026-04-23)')
print('='*70)

for code, name in STOCKS:
    try:
        h = yf.Ticker(code+'.TW').history(period='65d')
        if len(h) < 60: 
            print('%s %s: 資料不足' % (code, name))
            continue
        
        close = float(h['Close'].iloc[-1])
        prev = float(h['Close'].iloc[-2])
        change = (close / prev - 1) * 100
        
        cl = list(h['Close'])
        ma20_val = np.mean(cl[-20:])
        ma60_val = np.mean(cl[-60:])
        bias = (close / ma20_val - 1) * 100
        
        # RSI
        d = np.diff(cl)
        g = np.where(d > 0, d, 0)
        l = np.where(d > 0, 0, -d)
        ag = np.mean(g[-14:])
        al = np.mean(l[-14:])
        rs = 100 - (100 / (1 + ag / al)) if al != 0 else 50
        
        # ATR
        trs = []
        for i in range(-15, 0):
            hi = float(h['High'].iloc[i])
            lo = float(h['Low'].iloc[i])
            cl_prev = float(h['Close'].iloc[i-1])
            trs.append(max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev)))
        atr = np.mean(trs) if trs else 30
        atr_pct = atr / close * 100
        
        arrow = '↑' if change > 0 else '↓'
        
        print()
        print('【%s %s】' % (code, name))
        print('  價格: %.2f (%s%.2f%%)' % (close, arrow, change))
        print('  RSI: %.1f' % rs)
        print('  MA20偏離: %+.2f%%' % bias)
        print('  ATR: %.2f%%' % atr_pct)
        print('  MA20: %.2f | MA60: %.2f' % (ma20_val, ma60_val))
        print('  MA20 > MA60:', 'Y' if ma20_val > ma60_val else 'N')
        
        # 建議
        if rs < 70 and abs(bias) < 5 and ma20_val > ma60_val and atr_pct >= 0.5:
            print('  建議: ✅ 可考慮進場')
        elif rs >= 70:
            print('  建議: ⚠️ RSI過高')
        elif abs(bias) >= 5:
            print('  建議: ⚠️ 偏離過大')
        else:
            print('  建議: ⚠️ 觀望')
        
    except Exception as e:
        print('%s %s: 錯誤 - %s' % (code, name, str(e)))

print()
print('='*70)
print(' 美股昨晚: SPY +1.01%, QQQ +1.67%, TSM +5.26%')
print(' 台股趨勢: 多頭排列，偏多操作')
print('='*70)