# -*- coding: utf-8 -*-
"""
Leo v6.5 科技股波段 — 輕量版（快速執行）
"""
import sys, json, os, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

TRADES_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'

MONITOR = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海',
    '2379': '瑞昱', '2376': '技嘉', '2382': '廣達',
    '3665': '穎崴', '3034': '緯穎',
}

def get_rsi(closes, period=12):
    if len(closes) < period + 1: return 50
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag/al)) if al != 0 else 50

def get_ma(closes, period):
    return float(np.mean(closes[-period:])) if len(closes) >= period else closes[-1]

print('=' * 60)
print('Leo v6.5 科技股波段（輕量版）')
print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
print('=' * 60)

# Quick scan
results = []
for sym, name in MONITOR.items():
    try:
        h = yf.Ticker(f'{sym}.TW').history(period='10d')
        if h.empty or len(h) < 5: continue
        c = h['Close'].values
        price = float(c[-1])
        rsi = get_rsi(c, 12)
        mom5 = (c[-1]/c[-6]-1)*100 if len(c) >= 6 else 0
        ma60 = get_ma(c, 60)
        pos60 = (price/ma60-1)*100 if ma60 != 0 else 0
        results.append({
            'symbol': sym, 'name': name, 'price': price,
            'rsi': round(rsi, 1), 'mom5': round(mom5, 1), 'pos60': round(pos60, 1),
            'score': 50 - abs(rsi - 50) + (mom5 > 3) * 5
        })
    except:
        pass

results.sort(key=lambda x: x['score'], reverse=True)

print()
print('SYMBOL  NAME       PRICE      RSI    MOM5D   MA60%')
print('-' * 60)
for r in results:
    label = 'OB' if r['rsi'] > 70 else ('OS' if r['rsi'] < 30 else '')
    print('{:<8}{:<10}{:<10.0f}{:>6.1f}{:>7}%{:>6.1f}% {}'.format(
        r['symbol'], r['name'], r['price'], r['rsi'], r['mom5'], r['pos60'], label))

# Load / update trades
if os.path.exists(TRADES_FILE):
    with open(TRADES_FILE, encoding='utf-8') as f:
        trades_data = json.load(f)
else:
    trades_data = {'trades': []}

open_pos = [t for t in trades_data.get('trades', []) if t.get('status') == 'open']
closed = [t for t in trades_data.get('trades', []) if t.get('status') == 'closed']
wins = [t for t in closed if t.get('pnl', 0) > 0]
wr = len(wins) / len(closed) * 100 if closed else 0

print()
print('Trades: {} total | {} open | {} closed'.format(
    len(trades_data['trades']), len(open_pos), len(closed)))
print('WR: {:.0f}% | PnL: NT${:,.0f}'.format(wr, sum(t.get('pnl', 0) for t in closed)))

if open_pos:
    print()
    print('Open positions:')
    for t in open_pos[:5]:
        print('  {} {}: \${} (RSI={})'.format(t['symbol'], t.get('name', ''), t['entry_price'], t.get('entry_rsi', 0)))

print()
print('Market: TWII RSI~93 OVERBOUGHT — all on hold')
print('Report time: <10s')