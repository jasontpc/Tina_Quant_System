import yfinance as yf
import datetime

print("=" * 60)
print("TINA 風控檢查 - 完整報告")
print("=" * 60)

# TWII
ticker = yf.Ticker("^TWII")
hist = ticker.history(period="1mo")
print(f"TWII history rows: {len(hist)}")
if len(hist) > 0:
    print(f"TWII Last date: {hist.index[-1]}")
    print(f"TWII Last close: {hist['Close'].iloc[-1]:,.0f}")
    
    if len(hist) > 14:
        delta = hist["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        print(f"TWII RSI(14): {current_rsi:.1f}")
        
        if current_rsi > 85:
            status = "FIRE 極端過熱"
        elif current_rsi > 70:
            status = "HOT 過熱"
        elif current_rsi > 40:
            status = "NORMAL 正常"
        else:
            status = "COLD 超賣"
        print(f"市場狀態: {status}")

print("=" * 60)