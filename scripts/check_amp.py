import yfinance as yf

t = yf.Ticker('AMP')
info = t.info
hist = t.history(period='3mo')

print('=== AMP (Amplitude) ===')
print(f'現價: {info.get("currentPrice", info.get("regularMarketPrice"))}')
print(f'52週高: {info.get("fiftyTwoWeekHigh")}')
print(f'52週低: {info.get("fiftyTwoWeekLow")}')
print(f'Beta: {info.get("beta")}')
print(f'PER: {info.get("trailingPE")}')
print(f'EPS: {info.get("trailingEps")}')

# 近30日
closes = hist['Close'].tail(30)
print()
print('近30日:')
for date, close in closes.items():
    if close == closes.iloc[-1] or close == closes.iloc[0] or close == closes.iloc[14]:
        print(f'  {date.strftime("%m/%d")}: ${close:.2f}')

# RSI 計算
delta = closes.diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))
print(f'RSI(14): {rsi.iloc[-1]:.1f}')

# 均線
ma5 = hist['Close'].tail(20).rolling(5).mean()
ma20 = hist['Close'].tail(60).rolling(20).mean()
print()
print('=== 均線 ===')
print(f'MA5: ${ma5.iloc[-1]:.2f}')
print(f'MA20: ${ma20.iloc[-1]:.2f}')
print(f'現價/MA5: {(closes.iloc[-1]/ma5.iloc[-1]-1)*100:+.2f}%')
print(f'現價/MA20: {(closes.iloc[-1]/ma20.iloc[-1]-1)*100:+.2f}%')

# 5日動能
print()
print('=== 5日動能 ===')
for i in range(5):
    idx = -5 + i
    date = closes.index[idx]
    c = closes.iloc[idx]
    prev = closes.iloc[idx-1]
    chg = (c/prev-1)*100
    print(f'{date.strftime("%m/%d")}: ${c:.2f} ({chg:+.2f}%)')

# 評估
print()
print('=== Tina 評估 ===')
r = rsi.iloc[-1]
ma5_v = ma5.iloc[-1]
ma20_v = ma20.iloc[-1]
c = closes.iloc[-1]

if r < 40:
    signal = '[LOW] 超賣'
elif r > 70:
    signal = '[HIGH] 過熱'
else:
    signal = '[MID] 中性'

print(f'Signal: {signal}')
print(f'Bias: {((c/ma5_v-1)*100):+.1f}% vs MA5')
print(f'Bias: {((c/ma20_v-1)*100):+.1f}% vs MA20')

# 52週位置
high = info.get('fiftyTwoWeekHigh', 550.18)
low = info.get('fiftyTwoWeekLow', 422.37)
pos_in_52w = (c - low) / (high - low) * 100
print(f'52週位置: {pos_in_52w:.0f}% ({low}={low:.0f} ~ {high}={high:.0f})')