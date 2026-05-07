# -*- coding: utf-8 -*-
"""
Ray DCA 市場分析 — 完整版（TW + US）
TW: 0050/00646/00878/00919
US: VOO/QQQ/VTI/SCHD/BND
VOO 70% + QQQ 30% = Jo 核心 DCA 組合
"""
import sys, json, os, time
import pandas as pd
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

REPORT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\reports\dca_market_brief.json'

# TW ETF DCA
ETFS_TW = [
    ('0050', '元大台灣50'),
    ('00646', '富邦S&P500'),
    ('00878', '國泰永續高息'),
    ('00919', '群益台灣精選高息'),
]

# US ETF DCA (VOO 70% + QQQ 30%)
ETFS_US = [
    ('VOO', 'Vanguard S&P500', 0.70),
    ('QQQ', 'Invesco QQQ', 0.30),
    ('VTI', 'Vanguard Total', 0.00),
    ('SCHD', 'Schwab Div', 0.00),
    ('BND', 'Vanguard Bond', 0.00),
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
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_bb(closes, period=20):
    sma = float(np.mean(closes[-period:]))
    std = float(np.std(closes[-period:]))
    upper = sma + 2 * std
    lower = sma - 2 * std
    bb_pct = (closes[-1] - lower) / (upper - lower) * 100 if upper > lower else 50
    return round(bb_pct, 1)

print('=' * 65)
print('Ray DCA 市場分析（TW + US）')
print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
print('=' * 65)

results = {'TW': [], 'US': []}

# === Market Proxies ===
# TW
try:
    twii = yf.Ticker('^TWII').history(period='30d')
    if not twii.empty:
        twii_price = float(twii['Close'].iloc[-1])
        twii_ma20 = get_ma(twii['Close'].values, 20)
        twii_pos = (twii_price / twii_ma20 - 1) * 100
        twii_rsi = get_rsi(twii['Close'].values)
        print(f'TWII: {twii_price:,.0f} ({twii_pos:+.1f}%) RSI={twii_rsi:.0f}')
except:
    twii_pos, twii_rsi = 0, 50

# US
try:
    spy = yf.Ticker('SPY').history(period='30d')
    if not spy.empty:
        spy_price = float(spy['Close'].iloc[-1])
        spy_ma20 = get_ma(spy['Close'].values, 20)
        spy_pos = (spy_price / spy_ma20 - 1) * 100
        spy_rsi = get_rsi(spy['Close'].values)
        print(f'SPY:  ${spy_price:.2f} ({spy_pos:+.1f}%) RSI={spy_rsi:.0f}')
except:
    spy_pos, spy_rsi = 0, 50

# === TW Section ===
print()
print('=== TW ETF DCA ===')
print(f'{"ETF":<14} {"Price":>8} {"Chg%":>6} {"MA60%":>6} {"RSI":>5} {"BB%":>5} {"Pos52w":>7} {"Action":>10}')
print('-' * 70)

hot_tw = twii_rsi > 80 or twii_pos > 20
warm_tw = twii_rsi > 65 or twii_pos > 10

for sym, name in ETFS_TW:
    try:
        h = yf.Ticker(f'{sym}.TW').history(period='90d')
        if h.empty: continue
        c = h['Close'].dropna().values
        if len(c) < 10: continue

        price = float(c[-1])
        prev = float(c[-2]) if len(c) > 1 else price
        chg = (price / prev - 1) * 100
        ma60 = get_ma(c, 60)
        pos60 = (price / ma60 - 1) * 100
        rsi = get_rsi(c, 14)
        bb = calc_bb(c)
        win52 = min(252, len(c))
        high52 = float(np.max(c[-win52:]))
        pos52 = (price / high52 - 1) * 100

        if hot_tw:
            action = 'HOLD x0'
        elif warm_tw:
            action = 'HOLD x0.5'
        elif rsi < 40 or pos52 < -15:
            action = 'BUY x1.5'
        elif rsi < 50 or pos52 < -5:
            action = 'BUY x1'
        else:
            action = 'DCA x1'

        print(f'{name:<14} {price:>8.2f} {chg:>+5.1f}% {pos60:>+5.1f}% {rsi:>5.1f} {bb:>5.0f}% {pos52:>+6.1f}% {action:>10}')
        results['TW'].append({
            'symbol': sym, 'name': name, 'price': price,
            'change': round(chg, 2), 'ma60_pos': round(pos60, 1),
            'rsi': round(rsi, 1), 'bb_pct': bb,
            'pos52': round(pos52, 1), 'action': action
        })
    except Exception as e:
        print(f'{name:<14} Error: {e}')

# === US Section ===
print()
print('=== US ETF DCA (VOO 70% + QQQ 30%) ===')
print(f'{"ETF":<22} {"Price":>8} {"Chg%":>6} {"MA60%":>6} {"RSI":>5} {"BB%":>5} {"Pos52w":>7} {"Action":>10}')
print('-' * 75)

hot_us = spy_rsi > 80
warm_us = spy_rsi > 65

for sym, name, target_pct in ETFS_US:
    try:
        h = yf.Ticker(sym).history(period='90d')
        if h.empty: continue
        c = h['Close'].dropna().values
        if len(c) < 10: continue

        price = float(c[-1])
        prev = float(c[-2]) if len(c) > 1 else price
        chg = (price / prev - 1) * 100
        ma60 = get_ma(c, 60)
        pos60 = (price / ma60 - 1) * 100
        rsi = get_rsi(c, 14)
        bb = calc_bb(c)
        win52 = min(252, len(c))
        high52 = float(np.max(c[-win52:]))
        pos52 = (price / high52 - 1) * 100

        if hot_us:
            action = 'HOLD x0'
        elif warm_us:
            action = 'DCA x1'
        elif rsi < 40 or pos52 < -15:
            action = 'BUY x1.5'
        elif rsi < 50 or pos52 < -5:
            action = 'BUY x1'
        elif rsi > 70:
            action = 'HOLD x0.5'
        else:
            action = 'DCA x1'

        star = '[*]' if target_pct > 0 else '   '
        print(f'{star}{name:<19} ${price:>7.2f} {chg:>+5.1f}% {pos60:>+5.1f}% {rsi:>5.1f} {bb:>5.0f}% {pos52:>+6.1f}% {action:>10}')
        results['US'].append({
            'symbol': sym, 'name': name, 'target_pct': target_pct,
            'price': price, 'change': round(chg, 2),
            'ma60_pos': round(pos60, 1), 'rsi': round(rsi, 1),
            'bb_pct': bb, 'pos52': round(pos52, 1), 'action': action
        })
    except Exception as e:
        print(f'{sym:<22} Error: {e}')

# === Summary ===
print()
print('=== SUMMARY ===')
print(f'TW: TWII RSI={twii_rsi:.0f} {"[HOT]" if hot_tw else "[OK]"}')
print(f'US: SPY RSI={spy_rsi:.0f} {"[HOT]" if hot_us else "[OK]"}')
print()

# Jo core: VOO + QQQ
voo_action = next((r['action'] for r in results['US'] if r['symbol'] == 'VOO'), 'N/A')
qqq_action = next((r['action'] for r in results['US'] if r['symbol'] == 'QQQ'), 'N/A')
print(f'Jo Core DCA (VOO 70% + QQQ 30%):')
print(f'  VOO → {voo_action}')
print(f'  QQQ → {qqq_action}')

if hot_tw or hot_us:
    print()
    print('!!! MARKET OVERBOUGHT — All DCA HOLD')
elif warm_tw or warm_us:
    print('  => Normal DCA execution')

# Save
os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': time.strftime('%Y-%m-%d %H:%M'),
        'twii_rsi': round(twii_rsi, 1), 'spy_rsi': round(spy_rsi, 1),
        'hot_tw': hot_tw, 'hot_us': hot_us,
        'results': results
    }, f, ensure_ascii=False, indent=2)

print()
print('Report:', REPORT_FILE)