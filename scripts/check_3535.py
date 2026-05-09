import yfinance as yf

t = yf.Ticker('3535.TW')
info = t.info
hist = t.history(period='5d')

print('=' * 50)
print(f"股票: {info.get('longName')} ({'3535.TW'})")
print(f"現價: NT${info.get('currentPrice')}")
print(f"昨收: NT${info.get('previousClose')}")
print(f"52週高: NT${info.get('fiftyTwoWeekHigh')}")
print(f"52週低: NT${info.get('fiftyTwoWeekLow')}")
print(f"成交量: {info.get('averageVolume'):,}")
print()
print('近5日K線:')
for idx, row in hist.tail(5).iterrows():
    date_str = idx.strftime('%Y-%m-%d')
    print(f"  {date_str} 收:{row['Close']:.0f} 開:{row['Open']:.0f} 高:{row['High']:.0f} 低:{row['Low']:.0f} 量:{row['Volume']:,}")
print()
print('=' * 50)