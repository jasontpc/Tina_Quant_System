import yfinance as yf

tk = yf.Ticker('^TWII')
h = tk.history(period='5y')

if len(h) < 100:
    print('Not enough data')
    exit()

monthly = h['Close'].resample('ME').last()

print('TW 加權指數 近5年 回撤月份')
print('='*60)

drawdowns = []
for i in range(1, len(monthly)):
    ret = (monthly.iloc[i] / monthly.iloc[i-1] - 1) * 100
    if ret < 0:
        date = str(monthly.index[i])[:7]
        drawdowns.append({'date': date, 'ret': ret})

drawdowns.sort(key=lambda x: x['ret'])

print(f"{'年月':<8} {'報酬':>8}  {'嚴重程度'}")
print('-'*40)
for d in drawdowns[:20]:
    severity = '[CRITICAL]' if d['ret'] < -8 else '[WARNING]' if d['ret'] < -5 else '[NOTICE]'
    print(f"{d['date']:<8} {d['ret']:>7.1f}%  {severity}")

print()
print('年度最大回撤')
print('-'*40)
years = {}
for d in drawdowns:
    year = d['date'][:4]
    if year not in years:
        years[year] = []
    years[year].append(d['ret'])

for year in sorted(years.keys()):
    worst = min(years[year])
    months = len([r for r in years[year] if r < 0])
    print(f'{year}: 最差 {worst:.1f}%, 下跌月 {months}次')