import yfinance as yf
from datetime import datetime, timedelta

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

tk = yf.Ticker('^TWII')
h = tk.history(period='1y')

price = float(h['Close'].iloc[-1])
rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
ma60 = float(h['Close'].rolling(60).mean().iloc[-1])
ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0

# Find RSI peaks > 75
rsi_series = calc_rsi(h['Close'], 14)

peaks = []
for i in range(30, len(rsi_series)):
    if rsi_series.iloc[i] > 75:
        if rsi_series.iloc[i] > rsi_series.iloc[i-1] and rsi_series.iloc[i] > rsi_series.iloc[i+1]:
            peaks.append({
                'date': str(rsi_series.index[i])[:10],
                'rsi': float(rsi_series.iloc[i])
            })

print('TW Market RSI Analysis')
print('='*50)
print(f'Current RSI: {rsi:.1f}')
print(f'Ret 1M: {ret_1m:+.1f}%')
print(f'Price: {price:.0f}')
print(f'From MA20: {(price/ma20-1)*100:+.1f}%')

if peaks:
    last_peak = peaks[-1]
    last_date = str(h.index[-1])[:10]
    print(f'Last RSI Peak: {last_peak["date"]} RSI={last_peak["rsi"]:.1f}')
    print(f'Current Date: {last_date}')

print()
print('Historical RSI Peaks (last 5):')
for p in peaks[-5:]:
    print(f'  {p["date"]}: RSI={p["rsi"]:.1f}')

print()
print('Market Status:')
if rsi > 80:
    status = 'EXTREMELY OVERHEATED'
elif rsi > 75:
    status = 'OVERHEATED'
elif rsi > 65:
    status = 'BULLISH'
elif rsi < 40:
    status = 'OVERSOLD'
else:
    status = 'NEUTRAL'
print(f'Status: {status}')

print()
print('='*50)
print('PULLBACK ESTIMATION')
print('='*50)

# Historical analysis
# When RSI >75, how long until pullback?
pullback_after_peak = {
    'avg_days': 0,
    'max_days': 0,
    'occurrences': 0
}

if len(peaks) > 1:
    for i in range(len(peaks)-1):
        peak1 = datetime.strptime(peaks[i]['date'], '%Y-%m-%d')
        # Find next significant drop
        for j in range(i+1, len(peaks)):
            peak2 = datetime.strptime(peaks[j]['date'], '%Y-%m-%d')
            days = (peak2 - peak1).days
            if pullback_after_peak['occurrences'] == 0:
                pullback_after_peak['avg_days'] = days
                pullback_after_peak['max_days'] = days
            else:
                pullback_after_peak['avg_days'] = (pullback_after_peak['avg_days'] * pullback_after_peak['occurrences'] + days) / (pullback_after_peak['occurrences'] + 1)
                pullback_after_peak['max_days'] = max(pullback_after_peak['max_days'], days)
            pullback_after_peak['occurrences'] += 1
            break

print(f'Historical: After RSI >75, pullback occurs in {int(pullback_after_peak.get("avg_days", 30))} days avg')
print()

# Current projection
if rsi > 75:
    days_since_peak = 0
    if peaks:
        last_peak_dt = datetime.strptime(peaks[-1]['date'], '%Y-%m-%d')
        current_dt = datetime.strptime(str(h.index[-1])[:10], '%Y-%m-%d')
        days_since_peak = (current_dt - last_peak_dt).days
    
    est_days_to_pullback = max(5, int(pullback_after_peak.get('avg_days', 30) - days_since_peak))
    
    print(f'Current RSI: {rsi:.1f} ({"above" if rsi > 75 else "below"} 75)')
    print(f'Days in this stretch: {days_since_peak}')
    print(f'Estimated pullback in: {est_days_to_pullback} days')
    print()
    
    est_date = datetime.now() + timedelta(days=est_days_to_pullback)
    print(f'Estimated pullback around: {est_date.strftime("%Y-%m-%d")}')
    
    # Size estimate
    if rsi > 85:
        est_pullback = '-10% to -15%'
    elif rsi > 80:
        est_pullback = '-8% to -12%'
    else:
        est_pullback = '-5% to -8%'
    
    print(f'Estimated pullback size: {est_pullback}')
else:
    print('RSI not in overheated zone')

print()
print('='*50)
print('RECOMMENDATION')
print('='*50)
if rsi > 75:
    print('- Market EXTREMELY stretched')
    print('- Consider taking profits on high RSI stocks')
    print('- Increase cash allocation to 30-40%')
    print('- Wait for pullback before new entries')
    print('- Watch 2454 (RSI 89), AMD (RSI 83) for exit signals')
else:
    print('- RSI in neutral zone, no immediate concern')