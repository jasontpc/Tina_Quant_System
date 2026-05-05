import yfinance as yf

tk = yf.Ticker('^TWII')
h = tk.history(period='10y')

monthly = h['Close'].resample('ME').last()

print('TW Taiwan Stock Market - Annual Drawdown Analysis')
print('='*60)
print('Historical Data: 10 Years (2016-2026)')
print()

# Calculate annual returns
years_data = {}
for i in range(1, len(monthly)):
    year = monthly.index[i].year
    month_ret = (monthly.iloc[i] / monthly.iloc[i-1] - 1) * 100
    
    if year not in years_data:
        years_data[year] = []
    years_data[year].append({'month': str(monthly.index[i])[:7], 'ret': month_ret})

# Annual analysis
annual_summary = []
for year in sorted(years_data.keys()):
    returns = years_data[year]
    worst_month = min(returns, key=lambda x: x['ret'])
    best_month = max(returns, key=lambda x: x['ret'])
    total_return = (1 + sum([r['ret']/100 for r in returns])) - 1
    drawdown_months = [r for r in returns if r['ret'] < 0]
    
    annual_summary.append({
        'year': year,
        'worst': worst_month,
        'best': best_month,
        'total': total_return * 100,
        'drawdown_count': len(drawdown_months)
    })

# Sort by worst drawdown
annual_summary.sort(key=lambda x: x['worst']['ret'])

print('ANNUAL DRAWDOWN RANKING (Worst to Best)')
print('-'*60)
for a in annual_summary:
    severity = '[CRITICAL]' if a['worst']['ret'] < -8 else '[WARNING]' if a['worst']['ret'] < -5 else '[MILD]'
    print(f"{a['year']} | Worst: {a['worst']['month']} ({a['worst']['ret']:>+6.1f}%) {severity} | Best: {a['best']['month']} ({a['best']['ret']:>+6.1f}%) | YTD: {a['total']:>+7.1f}%")

print()
print('KEY DRAWDOWN PERIODS')
print('-'*60)

# Find severe drawdowns
severe = []
for year_data in years_data.values():
    for month in year_data:
        if month['ret'] < -8:
            severe.append(month)

severe.sort(key=lambda x: x['ret'])

print('Severe Drawdowns (>8% monthly):')
for s in severe[:10]:
    print(f"  {s['month']}: {s['ret']:>+.1f}%")

print()
print('RECOVERY ANALYSIS')
print('-'*60)

# Analyze recovery time (months to new high after drawdown)
cumulative_high = 0
recoveries = []

for i in range(1, len(monthly)):
    if cumulative_high == 0 or monthly.iloc[i] > cumulative_high:
        cumulative_high = monthly.iloc[i]
    
    month_ret = (monthly.iloc[i] / monthly.iloc[i-1] - 1) * 100
    
    if month_ret < -5:
        # Find how many months to recover
        pre_drop = monthly.iloc[i-1]
        for j in range(i+1, len(monthly)):
            if monthly.iloc[j] >= pre_drop:
                recovery_months = j - i
                recoveries.append({
                    'drop_month': str(monthly.index[i])[:7],
                    'drop_pct': month_ret,
                    'recovery_months': recovery_months
                })
                break

if recoveries:
    recoveries.sort(key=lambda x: x['drop_pct'])
    print('Major Drop & Recovery Times:')
    for r in recoveries[:8]:
        print(f"  {r['drop_month']}: -{r['drop_pct']:.1f}% -> Recovery in {r['recovery_months']} months")
else:
    print('No major drops requiring recovery analysis')

print()
print('STATISTICS')
print('-'*60)
all_returns = []
for year_data in years_data.values():
    for month in year_data:
        all_returns.append(month['ret'])

avg = sum(all_returns) / len(all_returns)
negative = [r for r in all_returns if r < 0]
worst = min(all_returns)

print(f'Total months analyzed: {len(all_returns)}')
print(f'Average monthly return: {avg:+.2f}%')
print(f'Worst month: {worst:+.1f}%')
print(f'Negative months: {len(negative)} ({len(negative)/len(all_returns)*100:.1f}%)')
print(f'Positive months: {len(all_returns)-len(negative)} ({(len(all_returns)-len(negative))/len(all_returns)*100:.1f}%)')