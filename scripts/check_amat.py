import yfinance as yf

print('=== AMAT 分析 | 2026-05-08 ===')
print()

t = yf.Ticker('AMAT')
info = t.info

curr = info.get('currentPrice', 0)
chg = info.get('regularMarketChange', 0)
chg_pct = info.get('regularMarketChangePercent', 0)

print(f'現價: ${curr:.2f}')
print(f'今日變化: {chg:+.2f} ({chg_pct:+.2%})')
print()

high52 = info.get('fiftyTwoWeekHigh', 0)
low52 = info.get('fiftyTwoWeekLow', 0)
dist_high = ((curr - high52) / high52 * 100) if high52 else 0
dist_low = ((curr - low52) / low52 * 100) if low52 else 0

print(f'52W 高: ${high52:.2f} (偏離: {dist_high:+.1f}%)')
print(f'52W 低: ${low52:.2f} (偏離: {dist_low:+.1f}%)')
print()

pe = info.get('trailingPE', 0)
eps = info.get('trailingEps', 0)
mktcap = info.get('marketCap', 0)
print(f'PE: {pe:.1f}' if pe else 'PE: N/A')
print(f'EPS: ${eps:.2f}' if eps else 'EPS: N/A')
if mktcap:
    print(f'市值: ${mktcap/1e9:.1f}B')
print()

rec = info.get('recommendationKey', 'N/A')
target = info.get('targetMeanPrice', 0)
if target and curr:
    upside = (target - curr) / curr * 100
    print(f'分析師目標: ${target:.2f} (潛在上漲: {upside:+.1f}%)')
print(f'建議: {rec}')
print()

hist = t.history(period='5d')
print('近5日:')
for idx, row in hist.iterrows():
    date_str = idx.strftime('%Y-%m-%d')
    close = row['Close']
    vol = int(row['Volume'])
    print(f'  {date_str}: ${close:.2f} Vol={vol:,}')
print()

# Jo 持倉成本
cost = 429.0
pnl = (curr - cost) / cost * 100
print(f'Jo 持倉: 4股 @ ${cost:.2f}')
print(f'現值: ${curr*4:.2f} | 損益: {pnl:+.2%} (${(curr-cost)*4:+.2f})')
print()

# 風控檢查
print('=== 風控檢查 ===')
if curr > high52 * 0.95:
    print('[WARNING] 接近52週高點，留意獲利了結')
if pnl > 5:
    print('[INFO] 已達止盈目標，可考慮分批賣出')
print(f'現價 ${curr:.2f} vs 成本 ${cost:.2f} = {pnl:+.2%}')