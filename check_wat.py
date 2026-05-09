import yfinance as yf
from datetime import datetime

ticker = yf.Ticker('WAT')
info = ticker.info

print('=== Waters Corporation (WAT) 基本資料 ===')
print('取得時間：' + datetime.now().strftime('%Y-%m-%d %H:%M'))
print()
print('股價：', info.get('currentPrice') or info.get('regularMarketPrice'), 'USD')
print('今日開盤：', info.get('regularMarketOpen'), 'USD')
print('今日高：', info.get('regularMarketDayHigh'), 'USD')
print('今日低：', info.get('regularMarketDayLow'), 'USD')
print('52週高：', info.get('fiftyTwoWeekHigh'), 'USD')
print('52週低：', info.get('fiftyTwoWeekLow'), 'USD')
print()
print('總市值：', f"{info.get('marketCap', 0):,}" if info.get('marketCap') else 'N/A')
print('成交量：', f"{info.get('regularMarketVolume', 0):,}" if info.get('regularMarketVolume') else 'N/A')
print('平均成交量：', f"{info.get('averageVolume', 0):,}" if info.get('averageVolume') else 'N/A')
print()
hist = ticker.history(period='5d', interval='1d')
print('=== 近五日日線 ===')
for date, row in hist.iterrows():
    change = row['Close'] - row['Open']
    pct = change / row['Open'] * 100
    sign = '+' if change > 0 else ''
    print(str(date)[:10], '開', round(row['Open'],2), '高', round(row['High'],2), '低', round(row['Low'],2), '收', round(row['Close'],2), sign+str(round(pct,1))+'%', '量', f"{int(row['Volume']):,}")