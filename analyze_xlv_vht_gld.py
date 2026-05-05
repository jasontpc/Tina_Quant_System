# -*- coding: utf-8 -*-
"""XLV / VHT / GLD 詳細分析"""
import sys, yfinance, sqlite3
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

etfs = [('XLV', 'Health Care Select Sector SPDR'),
        ('VHT', 'Vanguard Health Care ETF'),
        ('GLD', 'SPDR Gold Shares')]

def calc_rsi(closes, period=14):
    if len(closes) < period + 1: return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

for sym, name in etfs:
    print(f'\n=== {sym} {name} ===')
    t = yfinance.Ticker(sym)
    h = t.history(period='1y')
    if len(h) > 0:
        closes = h['Close'].tolist()
        current = closes[-1]
        high_52w = max(closes)
        low_52w = min(closes)
        from_high = (current - high_52w) / high_52w * 100
        from_low = (current - low_52w) / low_52w * 100
        
        rsi_14 = calc_rsi(closes, 14)
        rsi_7 = calc_rsi(closes, 7)
        rsi_28 = calc_rsi(closes, 28)
        
        ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current
        ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else ma20
        ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else ma50
        
        trend = '多頭' if current > ma200 > ma50 > ma20 else '震盪' if current > ma200 else '空頭'
        
        print(f'現價: ${current:.2f}')
        print(f'52w高: ${high_52w:.2f} ({from_high:+.1f}%)')
        print(f'52w低: ${low_52w:.2f} ({from_low:+.1f}%)')
        print(f'RSI(14): {rsi_14:.1f}')
        print(f'RSI(7): {rsi_7:.1f}')
        print(f'RSI(28): {rsi_28:.1f}')
        print(f'MA20: ${ma20:.2f} ' + ('↑' if current > ma20 else '↓'))
        print(f'MA50: ${ma50:.2f} ' + ('↑' if current > ma50 else '↓'))
        print(f'MA200: ${ma200:.2f} ' + ('↑' if current > ma200 else '↓'))
        print(f'趨勢: {trend}')
        
        info = t.info
        div_yield = info.get('dividendYield', 0) or 0
        if div_yield > 1: div_yield /= 100
        beta = info.get('beta', 0) or 0
        pe = info.get('trailingPE', 0) or 0
        eps = info.get('trailingEps', 0) or 0
        mkt_cap = info.get('marketCap', 0) or 0
        
        print(f'殖利率: {div_yield*100:.2f}%')
        print(f'Beta: {beta:.2f}')
        print(f'PE: {pe:.1f}')
        if eps: print(f'EPS: ${eps:.2f}')
        if mkt_cap > 0: print(f'規模: ${mkt_cap/1e9:.1f}B')
        
        # DCA score
        score = 0
        if rsi_14 < 40: score += 30
        if rsi_14 < 30: score += 20
        if from_high < -10: score += 20
        if current > ma200: score += 15
        if div_yield > 0.02: score += 15
        
        print(f'DCA分數: {score}/100')