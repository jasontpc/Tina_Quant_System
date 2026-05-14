import yfinance as yf
import json
import numpy as np

positions_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\portfolio\positions.json'
with open(positions_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

symbols = [p['symbol'] for p in data['positions']] + ['^TWII']
quotes = {}

for sym in symbols:
    tk = yf.Ticker(sym)
    hist = tk.history(period='60d')
    closes = hist['Close'].values
    high = hist['High'].iloc[-1]
    low = hist['Low'].iloc[-1]

    # RSI(14)
    deltas = np.diff(closes)
    gains = deltas[-14:][deltas[-14:] > 0]
    losses = -deltas[-14:][deltas[-14:] < 0]
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0
    rs = avg_gain / avg_loss if avg_loss != 0 else 999
    rsi = 100 - (100 / (1 + rs))

    ma20 = closes[-20:].mean() if len(closes) >= 20 else closes.mean()

    # MACD (EMA12/26, signal 9)
    ema12 = np.mean(closes[-12:])  # rough
    ema26 = np.mean(closes[-26:]) if len(closes) >= 26 else np.mean(closes)
    macd_line = ema12 - ema26
    macd_signal = macd_line * 0.9  # rough
    macd_hist = macd_line - macd_signal

    quotes[sym] = {
        'close': closes[-1],
        'prev_close': closes[-2],
        'open': hist['Open'].iloc[-1],
        'high': high,
        'low': low,
        'rsi14': rsi,
        'ma20': ma20,
        'macd_hist': macd_hist
    }

# TWII RSI
twii_closes = quotes['^TWII']['close']
hist60 = yf.Ticker('^TWII').history(period='60d')['Close'].values
deltas = np.diff(hist60)
gains = deltas[-14:][deltas[-14:] > 0]
losses = -deltas[-14:][deltas[-14:] < 0]
avg_gain = np.mean(gains) if len(gains) > 0 else 0
avg_loss = np.mean(losses) if len(losses) > 0 else 0
rs = avg_gain / avg_loss if avg_loss != 0 else 999
twii_rsi = 100 - (100 / (1 + rs))

print(f"TWII: close={twii_closes:.1f}, RSI={twii_rsi:.1f}")
for sym in [s for s in symbols if s != '^TWII']:
    q = quotes[sym]
    cost = next(p['cost'] for p in data['positions'] if p['symbol'] == sym)
    shares = next(p['shares'] for p in data['positions'] if p['symbol'] == sym)
    pnl_pct = (q['close'] - cost) / cost * 100
    print(f"{sym}: close={q['close']:.1f}, cost={cost:.1f}, pnl={pnl_pct:.1f}%, rsi={q['rsi14']:.1f}, ma20={q['ma20']:.1f}, macd_hist={q['macd_hist']:.2f}")