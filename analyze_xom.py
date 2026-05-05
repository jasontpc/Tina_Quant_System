import sys; sys.stdout.reconfigure(encoding='utf-8')
import yfinance, sqlite3

# Get live data
t = yfinance.Ticker("XOM")
info = t.fast_info
hist = t.history(period='3mo')

closes = hist['Close'].tolist()
highs = hist['High'].tolist()
lows = hist['Low'].tolist()
dates = hist.index.strftime('%Y-%m-%d').tolist()
vols = hist['Volume'].tolist()

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0
    trs = []
    for i in range(1, min(period+1, len(closes))):
        tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]))
        trs.append(tr)
    return sum(trs) / len(trs)

price = closes[-1]
rsi = calc_rsi(closes)
atr = calc_atr(highs, lows, closes)

# SMA
ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20

# 52w
high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)

# Recent
print('=== XOM Exxon 當前數據 ===')
print(f'現價: ${price:.2f}')
print(f'RSI(14): {rsi:.1f}')
print(f'ATR(14): ${atr:.2f}')
print(f'SMA20: ${ma20:.2f} (偏離: {(price-ma20)/ma20*100:+.1f}%)')
print(f'SMA60: ${ma60:.2f} (偏離: {(price-ma60)/ma60*100:+.1f}%)')
print(f'52w High: ${high_52w:.2f} (距: {(price-high_52w)/high_52w*100:+.1f}%)')
print(f'52w Low: ${low_52w:.2f} (距: {(price-low_52w)/low_52w*100:+.1f}%)')

# Stop loss
print('\n=== 停損建議 ===')
print(f'1.5x ATR: ${price - 1.5*atr:.2f} ({(price - 1.5*atr)/price*100:+.1f}%)')
print(f'2.0x ATR: ${price - 2.0*atr:.2f} ({(price - 2.0*atr)/price*100:+.1f}%)')
print(f'MA20: ${ma20:.2f} ({(price-ma20)/price*100:+.1f}%)')

# Strategy
print('\n=== Maggy 策略進場分析 ===')
entry_rsi = 35
exit_rsi = 65
max_hold = 20
print(f'進場條件: RSI < {entry_rsi} → 當前 RSI={rsi:.1f} → {"✅ 進場" if rsi < entry_rsi else "❌ 觀望"}')
print(f'出場條件: RSI > {exit_rsi}')
print(f'最大持倉: {max_hold}天')

# Recent price history
print('\n=== 近30天收盤 ===')
for i in range(-30, 0):
    idx = len(closes) + i
    if idx >= 0:
        rsi_val = calc_rsi(closes[:idx+1])
        print(f'{dates[idx][:10]}: ${closes[idx]:.0f} RSI={rsi_val:.1f}')

# Load sim trades
sim_db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy_sim_trades.db'
conn = sqlite3.connect(sim_db)
cur = conn.cursor()
cur.execute("SELECT entry_date, exit_date, return_pct, holding_days, exit_reason FROM sim_trades WHERE symbol='XOM' AND status='CLOSED' ORDER BY entry_date DESC LIMIT 10")
print('\n=== XOM 歷史交易記錄 ===')
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'{r[0][:10]}~{r[1][:10]}: {r[2]:+.2f}% ({r[3]}天) {r[4]}')
else:
    print('無交易記錄')
conn.close()

# Oil price correlation
print('\n=== 風險提醒 ===')
print('- XOM 為能源股，與油價高度相關')
print('- RSI 23.9 嚴重超賣，可能是進場機會')
print('- 但需注意能源股波動性較大')
print('- 建議設定嚴格停損')