import sys; sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, yfinance, json
from datetime import datetime

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'

# Load Nana trades
trades_file = f'{DATA_DIR}\\teams\\nana\\autonomous_trades.json'
try:
    with open(trades_file, 'r', encoding='utf-8') as f:
        trades = json.load(f)
    # Filter 3034 trades
    trades_3034 = [t for t in trades if t.get('symbol') == '3034']
    print(f"=== Nana 歷史交易（3034）===")
    if trades_3034:
        for t in trades_3034:
            print(f"  {t.get('entry_date', 'N/A')} {t.get('side', '')} {t.get('entry_price', 0)}→{t.get('exit_price', 0)} {t.get('return_pct', 0):+.2f}% {t.get('holding_days', 0)}天 {t.get('exit_reason', '')}")
    else:
        print("  無3034交易記錄")
except Exception as e:
    print(f"Nana trades: {e}")

# Get historical RSI data
print("\n=== 3034 歷史 RSI ===")
t = yfinance.Ticker("3034.TW")
hist = t.history(period='1y')
closes = hist['Close'].tolist()
dates = hist.index.strftime('%Y-%m-%d').tolist()

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

# Get recent RSI values
print(f"近30天 RSI 範圍:")
for i in range(30, len(closes)):
    rsi = calc_rsi(closes[:i+1])
    date = dates[i]
    close = closes[i]
    if i >= len(closes) - 10:
        print(f"  {date}: {close:.0f}, RSI={rsi:.1f}")

# Current data
print(f"\n=== 3034 緯穎 當前數據 ===")
print(f"現價: {closes[-1]:.0f}")
print(f"RSI(14): {calc_rsi(closes):.1f}")

# SMA
ma20 = sum(closes[-20:]) / 20
ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else sum(closes) / len(closes)
print(f"SMA20: {ma20:.0f} (偏離: {(closes[-1]-ma20)/ma20*100:+.1f}%)")
print(f"SMA60: {ma60:.0f} (偏離: {(closes[-1]-ma60)/ma60*100:+.1f}%)")

# 52w
high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
print(f"52w高: {high_52w:.0f} (距: {(closes[-1]-high_52w)/high_52w*100:+.1f}%)")
print(f"52w低: {low_52w:.0f} (距: {(closes[-1]-low_52w)/low_52w*100:+.1f}%)")

# ATR
highs = hist['High'].tolist()
lows = hist['Low'].tolist()
trs = []
for i in range(1, min(15, len(closes))):
    tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]))
    trs.append(tr)
atr = sum(trs) / len(trs)
print(f"ATR(14): {atr:.1f}")

# Stop loss levels
print(f"\n=== 停損建議 ===")
print(f"1.5x ATR: {closes[-1] - 1.5*atr:.0f} ({(closes[-1] - 1.5*atr)/closes[-1]*100:+.1f}%)")
print(f"2.0x ATR: {closes[-1] - 2.0*atr:.0f} ({(closes[-1] - 2.0*atr)/closes[-1]*100:+.1f}%)")
print(f"MA20: {ma20:.0f} ({(closes[-1]-ma20)/closes[-1]*100:+.1f}%)")

# Check Nana's v6.8 parameters for 3034
print(f"\n=== Nana 波段系統狀態 ===")
print(f"3034 目前不在 Nana 主要候選名單中")
print(f"歷史表現: 無明確進場記錄")