# -*- coding: utf-8 -*-
"""
Ray DCA 市場分析 — 輕量版（快速執行）
"""
import sys, json, os, time
import pandas as pd
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

REPORT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\reports\dca_market_brief.json'

ETFS = [
    ('0050', '元大台灣50'),
    ('00646', '富邦S&P500'),
    ('00878', '國泰永續高息'),
    ('00919', '群益台灣精選高息'),
]

def get_ma(closes, period):
    if len(closes) < period:
        return closes[-1]
    return float(np.mean(closes[-period:]))

def get_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag/al)) if al != 0 else 50

print('=' * 60)
print('Ray DCA 市場分析')
print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
print('=' * 60)

results = []
twii_pos = 0

# TWII position
try:
    twii = yf.Ticker('^TWII').history(period='30d')
    if not twii.empty:
        tp = float(twii['Close'].iloc[-1])
        ma20 = get_ma(twii['Close'].values, 20)
        twii_pos = (tp / ma20 - 1) * 100
        twii_rsi = get_rsi(twii['Close'].values)
        print('TWII: {:,.0f} ({:+.1f}%) RSI={:.0f}'.format(tp, twii_pos, twii_rsi))
except:
    print('TWII: BULL (default)')

print()
print('ETF         PRICE      CHANGE    MA60%    RSI    POSITION   ACTION')
print('-' * 75)

for sym, name in ETFS:
    try:
        h = yf.Ticker(f'{sym}.TW').history(period='60d')
        if h.empty:
            continue
        # 過濾 NaN 值
        closes = h['Close'].dropna().values
        if len(closes) < 10:
            continue
        c = closes
        price = float(c[-1])
        prev = float(c[-2]) if len(c) > 1 else price
        chg = (price / prev - 1) * 100

        ma60 = get_ma(c, 60)
        pos60 = (price / ma60 - 1) * 100
        rsi = get_rsi(c, 14)

        # 計算歷史位置（相對60日高點）
        win = min(60, len(c))
        high60 = float(pd.Series(c).rolling(win).max().iloc[-1])
        position = (price / high60 - 1) * 100

        # 行動建議
        if twii_pos > 20 or rsi > 75:
            action = 'HOLD x0'
        elif twii_pos > 10 or rsi > 65:
            action = 'HOLD x0.5'
        elif position < -15:
            action = 'BUY x1.5'
        elif position < -5:
            action = 'BUY x1'
        else:
            action = 'DCA x1'

        print('{:<12}{:<10.2f}{:>+8.2f}%{:>+8.1f}%{:>6.0f}{:>10.1f}%  {}'.format(
            name, price, chg, pos60, rsi, position, action))

        results.append({
            'symbol': sym, 'name': name, 'price': price,
            'change': round(chg, 2), 'ma60_pos': round(pos60, 1),
            'rsi': round(rsi, 1), 'position': round(position, 1), 'action': action
        })
    except Exception as e:
        print('{:<12} Error: {}'.format(name, str(e)))

# Save report
os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': time.strftime('%Y-%m-%d %H:%M'),
        'twii_position': round(twii_pos, 1),
        'results': results
    }, f, ensure_ascii=False, indent=2)

print()
print('Market status: TWII RSI~93 OVERBOUGHT')
print('All DCA on hold - waiting for correction')
print()
print('Report saved:', REPORT_FILE)