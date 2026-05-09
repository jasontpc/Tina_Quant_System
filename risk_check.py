import yfinance as yf
import datetime

print("=" * 60)
print("TINA 風控檢查報告 - 2026-05-08 13:24")
print("=" * 60)

# Check TWII for market RSI
print("\n【大盤狀態】")
ticker = yf.Ticker("^TWII")
hist = ticker.history(period="5d")
if len(hist) > 14:
    delta = hist["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    current_price = hist["Close"].iloc[-1]
    print(f"TWII: {current_price:,.0f}")
    print(f"RSI(14): {current_rsi:.1f}")
    if current_rsi > 85:
        status = "FIRE 極端過熱 - 全面觀望"
    elif current_rsi > 70:
        status = "HOT 過熱 - 降低部位"
    elif current_rsi > 40:
        status = "NORMAL 正常區間"
    else:
        status = "COLD 超賣 - 尋找進場機會"
    print(f"市場狀態: {status}")

# Check 00713 Taiwan ETF
print("\n【持倉檢查 - 00713】")
ticker = yf.Ticker("00713.TW")
hist = ticker.history(period="3mo")
if len(hist) > 14:
    delta = hist["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    current_price = hist["Close"].iloc[-1]
    change_pct = (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100

    cost = 53.22
    pnl_pct = (current_price - cost) / cost * 100

    print(f"標的: 00713 元大高息低波")
    print(f"數量: 300股 @ ${cost}")
    print(f"現價: ${current_price:.2f}")
    print(f"帳面損益: {pnl_pct:+.2f}%")

    stop_loss = 51.00
    distance_to_sl = (current_price - stop_loss) / current_price * 100
    print(f"停損價: ${stop_loss} | 距離: {distance_to_sl:+.2f}%")
    print(f"目標價: $55.50")

    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
    ma60 = hist["Close"].rolling(60).mean().iloc[-1]
    print(f"MA20: ${ma20:.2f} | MA60: ${ma60:.2f}")

    buy_date = datetime.date(2026, 4, 30)
    today = datetime.date(2026, 5, 8)
    days_held = (today - buy_date).days
    danger_line = "YES" if days_held > 30 else "NO"
    print(f"持有天數: {days_held}天 | 超過30天危險線: {danger_line}")
    print(f"RSI(14): {current_rsi:.1f}")

    # Risk control evaluation
    print("\n【風控評估】")
    alerts = []
    if current_rsi > 65:
        alerts.append(f"RSI {current_rsi:.1f} > 65 進場上限")
    if days_held > 30:
        alerts.append(f"持有 {days_held} 天 > 30天 危險閾值")
    if pnl_pct < -4:
        alerts.append(f"虧損 {pnl_pct:.2f}% > 4%")

    if alerts:
        print("ALERT: " + "; ".join(alerts))
    else:
        print("PASS: 符合所有風控條件")
        if current_rsi < 65 and pnl_pct > -4:
            action = "持有，目標 $55.50"
            print(f"建議: {action}")
    print(f"日漲跌: {change_pct:+.2f}%")

print("\n" + "=" * 60)
print("風控檢查完成")
print("=" * 60)