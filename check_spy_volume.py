import yfinance as yf
from datetime import datetime

spy = yf.Ticker('SPY')
hist = spy.history(period='5d', interval='1d')

print('=== 近五日美股成交量（SPY）===')
print('取得時間：' + datetime.now().strftime('%Y-%m-%d %H:%M'))
print()
for i, (date, row) in enumerate(hist.iterrows()):
    vol = int(row['Volume'])
    vol_str = f'{vol:,}'
    change = ''
    if i > 0:
        prev_vol = int(hist.iloc[i-1]['Volume'])
        diff = vol - prev_vol
        pct = diff / prev_vol * 100 if prev_vol > 0 else 0
        sign = '+' if diff > 0 else ''
        change = f' ({sign}{diff:,} / {sign}{pct:.1f}%)'
    print(str(date)[:10] + '  成交量：' + vol_str + change)