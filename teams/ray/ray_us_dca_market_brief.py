# -*- coding: utf-8 -*-
"""
Ray US ETF DCA 市場分析 — VOO/QQQ 追蹤
VOO 70% + QQQ 30% Jo 的核心 DCA 組合
"""
import sys, json, os, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

REPORT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\reports\ray_us_dca_report.json'
ETFS = [
    ('VOO', 'Vanguard S&P500', 0.70),
    ('QQQ', 'Invesco QQQ', 0.30),
    ('VTI', 'Vanguard Total', 0.00),   # 可選
    ('SCHD', 'Schwab Div', 0.00),     # 衛星
    ('VYM', 'Vanguard HiYld', 0.00),  # 衛星
    ('BND', 'Vanguard Bond', 0.00),   # 平衡
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
    return float(100 - (100 / (1 + ag / al))) if al != 0 else 50.0

def calc_sma(closes, period):
    return float(np.mean(closes[-period:]))

def calc_stdev(closes, period):
    return float(np.std(closes[-period:]))

def calc_bb(closes, period=20):
    sma = calc_sma(closes, period)
    std = calc_stdev(closes, period)
    upper = sma + 2 * std
    lower = sma - 2 * std
    return upper, sma, lower

print('=' * 60)
print('Ray US ETF DCA — VOO/QQQ 追蹤')
print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
print('=' * 60)

results = []
spy_pos = 0

# SPY as market proxy
try:
    spy = yf.Ticker('SPY').history(period='30d')
    if not spy.empty:
        sp = float(spy['Close'].iloc[-1])
        sp_ma20 = get_ma(spy['Close'].values, 20)
        spy_pos = (sp / sp_ma20 - 1) * 100
        spy_rsi = get_rsi(spy['Close'].values)
        print(f'SPY: ${sp:.2f} MA20:{sp_ma20:.2f} ({spy_pos:+.1f}%) RSI={spy_rsi:.0f}')
except:
    print('SPY: BULL (default)')
    spy_rsi = 50

print()
print(f'{"ETF":<22} {"Price":>8} {"Chg%":>6} {"MA20":>8} {"MA60":>8} {"RSI":>5} {"BB%":>5} {"Pos":>7} {"Action":>12}')
print('-' * 95)

# Market status
hot = spy_rsi > 80
warm = spy_rsi > 65

for sym, name, target_pct in ETFS:
    try:
        h = yf.Ticker(sym).history(period='90d')
        if h.empty:
            continue
        closes = h['Close'].dropna().values
        if len(closes) < 20:
            continue

        price = float(closes[-1])
        prev = float(closes[-2]) if len(closes) > 1 else price
        chg = (price / prev - 1) * 100

        ma20 = get_ma(closes, 20)
        ma60 = get_ma(closes, 60)
        rsi = get_rsi(closes, 14)

        # BB position
        bb_upper, bb_mid, bb_lower = calc_bb(closes, 20)
        if bb_upper > bb_lower:
            bb_pct = (price - bb_lower) / (bb_upper - bb_lower) * 100
        else:
            bb_pct = 50

        # Position from 52w high
        win52 = min(252, len(closes))
        high52 = float(np.max(closes[-win52:]))
        pos52 = (price / high52 - 1) * 100

        # DCA Action logic
        if hot:
            action = 'HOLD x0'
        elif warm:
            action = 'DCA x1'
        elif rsi < 40:
            action = 'BUY x1.5'
        elif rsi < 50:
            action = 'BUY x1'
        elif rsi > 70:
            action = 'HOLD x0.5'
        else:
            action = 'DCA x1'

        # Highlight VOO/QQQ
        star = '***' if target_pct > 0 else '   '
        print(f'{star}{sym:<19} ${price:>7.2f} {chg:>+5.1f}% {ma20:>8.2f} {ma60:>8.2f} {rsi:>5.1f} {bb_pct:>5.0f}% {pos52:>+6.1f}% {action:>12}')

        results.append({
            'symbol': sym, 'name': name, 'target_pct': target_pct,
            'price': round(price, 2), 'change': round(chg, 2),
            'ma20': round(ma20, 2), 'ma60': round(ma60, 2),
            'rsi': round(rsi, 1), 'bb_pct': round(bb_pct, 1),
            'pos52': round(pos52, 1), 'action': action,
            'hot': hot, 'warm': warm, 'spy_rsi': round(spy_rsi, 1)
        })
    except Exception as e:
        print(f'{sym:<22} Error: {e}')

# Save report
os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': time.strftime('%Y-%m-%d %H:%M'),
        'spy_rsi': round(spy_rsi, 1),
        'market_hot': hot,
        'results': results
    }, f, ensure_ascii=False, indent=2)

print()
if hot:
    print('!!! MARKET OVERBOUGHT (SPY RSI={:.0f}) — All DCA on HOLD'.format(spy_rsi))
elif warm:
    print('  Market warm (SPY RSI={:.0f}) — Normal DCA'.format(spy_rsi))
else:
    print('  Market OK — DCA active')

print()
print('Note: VOO 70% + QQQ 30% = Jo core DCA portfolio')
print('VOO/QQQ monthly execution: last trading day of month')
print()
print('Report:', REPORT_FILE)