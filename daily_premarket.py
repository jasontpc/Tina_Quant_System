# -*- coding: utf-8 -*-
"""每日開盤前策略報告 v2 - 極速版"""
import sys, yfinance as yf, numpy as np
sys.stdout.reconfigure(encoding='utf-8')

try:
    # TWII
    twii = yf.Ticker('^TWII').history(period='5d')
    c = twii['Close'].dropna().values
    if len(c) < 2:
        print('Tina 每日開盤前策略報告')
        print('無足夠數據')
        sys.exit(0)
    
    twii_price = float(c[-1])
    twii_prev = float(c[-2])
    twii_chg = (twii_price / twii_prev - 1) * 100
    
    # RSI (精簡版)
    d = np.diff(c)
    g = np.maximum(d, 0)
    l = np.maximum(-d, 0)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    rsi = float(100 - (100 / (1 + ag / al))) if al != 0 else 50.0
    
    print('Tina 每日開盤前策略報告')
    print(f'時間: {twii_price:.2f} ({twii_chg:+.2f}%) RSI={rsi:.0f}')
    print()
    
    if rsi > 85:
        print('DCA: HOLD x0 (TWII 過熱)')
        print('Nana: WATCH (等待 RSI 降至 70 以下)')
        print('Leo: 等待 RSI 降至 40 以下')
        print('Overall: WATCH MODE (過熱)')
    elif rsi > 70:
        print('DCA: HOLD x0.5 (觀望)')
        print('Nana: WATCH (選擇性進場)')
        print('Leo: 等待 RSI 降至 50 以下')
        print('Overall: CAUTION')
    elif rsi > 40:
        print('DCA: DCA x1 (正常)')
        print('Nana: ACTIVE (選擇性進場)')
        print('Leo: 進場訊號關注')
        print('Overall: NEUTRAL')
    else:
        print('DCA: DCA x2 (加碼)')
        print('Nana: FULL (全力進場)')
        print('Leo: 積極進場')
        print('Overall: BULLISH')
        
except Exception as e:
    print(f'錯誤: {e}')
    print('DCA: HOLD x0')
    print('Overall: UNKNOWN')