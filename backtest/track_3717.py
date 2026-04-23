# -*- coding: utf-8 -*-
"""
3717 晶澈 - 上漲追蹤通知
"""

watchlist = ['3717.TW']

def check_rise():
    import yfinance as yf
    import numpy as np
    
    code = '3717'
    name = '晶澈'
    
    h = yf.Ticker(code+'.TW').history(period='5d')
    if len(h) < 2:
        print('資料不足')
        return
    
    prices = list(h['Close'])
    current = float(prices[-1])
    prev = float(prices[-2])
    change = (current / prev - 1) * 100
    
    # 計算 MA5
    ma5 = np.mean(prices[-5:]) if len(prices) >= 5 else current
    
    print('='*50)
    print(f' {code} {name} - 追蹤')
    print('='*50)
    print(f' 現價: {current:.2f}')
    print(f' 昨日: {prev:.2f}')
    print(f' 漲幅: {change:+.2f}%')
    print(f' MA5:  {ma5:.2f}')
    print()
    
    if change >= 3.0:
        print('🔥 上漲超過 3%！')
        return True
    elif change >= 1.0:
        print('↑ 上漲 1-3%')
        return False
    else:
        print('→ 漲幅不足')
        return False

if __name__ == '__main__':
    check_rise()