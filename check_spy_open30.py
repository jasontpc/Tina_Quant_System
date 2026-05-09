import yfinance as yf
from datetime import datetime, timedelta

spy = yf.Ticker('SPY')

# Get 5min data for last 5 trading days
hist = spy.history(period='5d', interval='5m')

# Collect daily opening 30-min volume
daily_opening_vol = {}
for date, row in hist.iterrows():
    day = str(date)[:10]
    hour = date.hour
    minute = date.minute
    # 09:30-10:00 = first 30 min
    if hour == 9 and minute <= 30:
        if day not in daily_opening_vol:
            daily_opening_vol[day] = 0
        daily_opening_vol[day] += int(row['Volume'])

# Sort by date
sorted_days = sorted(daily_opening_vol.keys())

print('=== 近五日美股開盤30分鐘成交量（SPY）===')
print('取得時間：' + datetime.now().strftime('%Y-%m-%d %H:%M'))
print()
for i, day in enumerate(sorted_days):
    vol = daily_opening_vol[day]
    change = ''
    if i > 0:
        prev_vol = daily_opening_vol[sorted_days[i-1]]
        diff = vol - prev_vol
        pct = diff / prev_vol * 100 if prev_vol > 0 else 0
        sign = '+' if diff > 0 else ''
        change = f' ({sign}{diff:,} / {sign}{pct:.1f}%)'
    print(day + '  開盤30分鐘：' + f'{vol:,}' + change)