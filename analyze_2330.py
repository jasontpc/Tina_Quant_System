# -*- coding: utf-8 -*-
import sys, yfinance
sys.stdout.reconfigure(encoding='utf-8')

sym = '2330.TW'
print(f'=== 2330 台積電 分析（15:26） ===\n')

t = yfinance.Ticker(sym)
info = t.fast_info
price = info.get('lastPrice') or info.get('regularMarketPrice')
prev = info.get('previousClose')
open_p = info.get('open')
high = info.get('dayHigh')
low = info.get('dayLow')
chg = ((price - prev) / prev * 100) if price and prev else 0

print(f'現在價格: {price:.0f} ({chg:+.1f}%)')
print(f'開盤: {open_p:.0f} | 高: {high:.0f} | 低: {low:.0f}')
print(f'昨收: {prev:.0f}')

# Historical for RSI/MA
hist = t.history(period='3mo')
closes = hist['Close'].tolist()
highs = hist['High'].tolist()
lows = hist['Low'].tolist()

# RSI(14)
gains = []
losses = []
for i in range(1, len(closes)):
    diff = closes[i] - closes[i-1]
    gains.append(diff if diff > 0 else 0)
    losses.append(abs(diff) if diff < 0 else 0)

avg_gain = sum(gains[-14:]) / 14
avg_loss = sum(losses[-14:]) / 14
rs = avg_gain / avg_loss if avg_loss > 0 else 100
rsi = 100 - (100 / (1 + rs))

# SMA
sma20 = sum(closes[-20:]) / 20
sma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else 0

# MA偏離
ma20_dev = (price - sma20) / sma20 * 100
ma60_dev = (price - sma60) / sma60 * 100 if sma60 else 0

# ATR(14) - manually
trs = []
for i in range(1, 15):
    idx = -i
    tr = max(closes[idx] - lows[idx], highs[idx] - closes[idx-1])
    trs.append(tr)
atr = sum(trs) / 14

# 52w
high_52w = max(hist['High'].tolist()[-252:])
low_52w = min(hist['Low'].tolist()[-252:])
from_high = (price - high_52w) / high_52w * 100
from_low = (price - low_52w) / low_52w * 100

print(f'\n📊 技術指標:')
print(f'  RSI(14): {rsi:.1f}')
print(f'  SMA(20): {sma20:.0f}')
print(f'  SMA(60): {sma60:.0f}')
print(f'  MA20偏離: {ma20_dev:+.1f}%')
print(f'  MA60偏離: {ma60_dev:+.1f}%')
print(f'  ATR(14): {atr:.0f}')
print(f'  52w高點: {high_52w:.0f}')
print(f'  52w低點: {low_52w:.0f}')
print(f'  距高點: {from_high:+.1f}%')
print(f'  距低點: {from_low:+.1f}%')

print(f'\n⚠️ 信號評估:')
if rsi > 80:
    status = '🔴 過熱'
elif rsi > 60:
    status = '🟡 偏熱'
elif rsi < 40:
    status = '🟢 超賣'
else:
    status = '⚪ 中性'
print(f'  RSI: {rsi:.1f} → {status}')
print(f'  MA20: {"✅ 多頭" if price > sma20 else "❌ 空頭"} (偏離{ma20_dev:+.1f}%)')
print(f'  52w高點: {from_high:+.1f}%')

print(f'\n💰 風險:')
print(f'  現價: {price:.0f}')
if atr > 0:
    sl15 = price - atr * 1.5
    sl20 = price - atr * 2
    print(f'  ATR: {atr:.0f}')
    print(f'  1.5x ATR 止損: {sl15:.0f} (-{(atr*1.5/price)*100:.1f}%)')
    print(f'  2x ATR 止損: {sl20:.0f} (-{(atr*2/price)*100:.1f}%)')

print(f'\n📋 結論:')
if rsi > 80:
    print('  ⚠️ 短線過熱，回調風險高')
    print('  法人動能弱，不建議追高')
elif rsi > 60:
    print('  🟡 偏熱，但動能放緩')
    print('  持有多單可續抱，設好停利')
else:
    print('  ✅ RSI 中性，觀望')