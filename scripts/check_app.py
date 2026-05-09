import yfinance as yf

print('=== APP 分析 | 2026-05-08 ===')
print()

t = yf.Ticker('APP')
info = t.info

print(f'名稱: {info.get("longName", "N/A")}')
print(f'現價: ${info.get("currentPrice", info.get("regularMarketPrice", "N/A"))}')
chg = info.get('regularMarketChange', 0)
chg_pct = info.get('regularMarketChangePercent', 0)
print(f'今日變化: {chg:+.2f} ({chg_pct:+.2%})')
print()

# 52週
high52 = info.get('fiftyTwoWeekHigh', 0)
low52 = info.get('fiftyTwoWeekLow', 0)
curr = info.get('currentPrice', 0)
dist_high = ((curr - high52) / high52 * 100) if high52 else 0
dist_low = ((curr - low52) / low52 * 100) if low52 else 0

print(f'52週高: ${high52:.2f} (偏離: {dist_high:+.1f}%)')
print(f'52週低: ${low52:.2f} (偏離: {dist_low:+.1f}%)')
print()

# 估值
pe = info.get('trailingPE', 0)
eps = info.get('trailingEps', 0)
mktcap = info.get('marketCap', 0)
if mktcap:
    print(f'PE: {pe:.1f}' if pe else 'PE: N/A')
    print(f'EPS: ${eps:.2f}' if eps else 'EPS: N/A')
    print(f'市值: ${mktcap/1e9:.1f}B')
print()

# 近期歷史
hist = t.history(period='5d')
print('近5日:')
for idx, row in hist.iterrows():
    print(f'  {idx.strftime("%Y-%m-%d")}: ${row["Close"]:.2f} ({row["Volume"]:,} shares)')
print()

# 分析師目標
rec = info.get('recommendationKey', 'N/A')
target = info.get('targetMeanPrice', 0)
if target:
    upside = (target - curr) / curr * 100
    print(f'分析師目標價: ${target:.2f} (潛在上漲: {upside:+.1f}%)')
print(f'建議: {rec}')
print()

# 檢查成本（假設 Jo 可能持有）
print('=== 警示 ===')
if curr < low52 * 1.05:
    print('⚠️ 接近52週低點，注意跌破風險')
if chg_pct < -5:
    print('🔴 今日跌幅 > 5%，關注是否為系統性風險')
print()
print(f'現價 ${curr:.2f} vs 52W高 ${high52:.2f} = 回調 {abs(dist_high):.1f}%')