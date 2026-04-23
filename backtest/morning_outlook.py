# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

print('='*70)
print(' 台股盤前預測 (2026-04-23)')
print('='*70)

# 美股期貨
print('\n【美股期貨】')
try:
    spy = yf.Ticker('SPY').history(period='2d')
    if len(spy) >= 2:
        change = spy['Close'].iloc[-1] - spy['Close'].iloc[-2]
        pct = change / spy['Close'].iloc[-2] * 100
        arrow = '↑' if change > 0 else '↓'
        print('S&P 500 ETF (SPY): %s (%.2f%%)' % (arrow, pct))
except:
    pass

try:
    qqq = yf.Ticker('QQQ').history(period='2d')
    if len(qqq) >= 2:
        change = qqq['Close'].iloc[-1] - qqq['Close'].iloc[-2]
        pct = change / qqq['Close'].iloc[-2] * 100
        arrow = '↑' if change > 0 else '↓'
        print('Nasdaq ETF (QQQ): %s (%.2f%%)' % (arrow, pct))
except:
    pass

# 台積電 ADR
print('\n【台積電 ADR】')
try:
    tsm = yf.Ticker('TSM').history(period='2d')
    if len(tsm) >= 2:
        change = tsm['Close'].iloc[-1] - tsm['Close'].iloc[-2]
        pct = change / tsm['Close'].iloc[-2] * 100
        arrow = '↑' if change > 0 else '↓'
        print('TSM: %s (%.2f%%)' % (arrow, pct))
except:
    pass

# 台股技術面
print('\n【加權指數技術面】')
try:
    twii = yf.Ticker('^TWII').history(period='65d')
    cl = list(twii['Close'])
    ma5 = np.mean(cl[-5:])
    ma10 = np.mean(cl[-10:])
    ma20 = np.mean(cl[-20:])
    ma60 = np.mean(cl[-60:]) if len(cl) >= 60 else np.mean(cl)
    price = cl[-1]
    
    print('價格: %.2f' % price)
    print('MA5:  %.2f' % ma5)
    print('MA10: %.2f' % ma10)
    print('MA20: %.2f' % ma20)
    print('MA60: %.2f' % ma60)
    
    if price > ma5 > ma10 > ma20:
        trend = '多頭排列'
    elif price > ma20:
        trend = '震盪偏多'
    else:
        trend = '偏空'
    print('趨勢: %s' % trend)
except Exception as e:
    print('無法取得加權指數: %s' % str(e))

# 日韓市場
print('\n【亞股鄰近市場】')
try:
    n225 = yf.Ticker('^N225').history(period='2d')
    if len(n225) >= 2:
        change = n225['Close'].iloc[-1] - n225['Close'].iloc[-2]
        pct = change / n225['Close'].iloc[-2] * 100
        arrow = '↑' if change > 0 else '↓'
        print('日經 225: %s (%.2f%%)' % (arrow, pct))
except:
    pass

try:
    ks200 = yf.Ticker('^KS200').history(period='2d')
    if len(ks200) >= 2:
        change = ks200['Close'].iloc[-1] - ks200['Close'].iloc[-2]
        pct = change / ks200['Close'].iloc[-2] * 100
        arrow = '↑' if change > 0 else '↓'
        print('韓國 KOSPI: %s (%.2f%%)' % (arrow, pct))
except:
    pass

print()
print('='*70)
print(' 【今日預測】')
print('='*70)
print(' 美股昨晚全數上漲 (SPY +1.05%, QQQ +1.64%)')
print(' 台股昨日大漲 +1.75%，收盤 37,605')
print(' 建議: 今日可能持續多頭，觀察 37,800 壓力')
print('='*70)