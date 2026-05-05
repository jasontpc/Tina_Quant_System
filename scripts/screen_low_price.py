import yfinance as yf
import json

# Expanded TW stock list (major mid/small cap)
tw_stocks = [
    # Top chips/tech
    '2330.TW', '2382.TW', '2317.TW', '2454.TW', '3034.TW', '3665.TW',
    '2371.TW', '3532.TW', '3443.TW', '4952.TW', '2303.TW', '3036.TW',
    '2451.TW', '2327.TW', '2458.TW', '3037.TW', '3661.TW',
    '6415.TW', '3552.TW', '4958.TW', '6183.TW', '6285.TW',
    # More mid cap
    '2301.TW', '2303.TW', '2324.TW', '2337.TW', '2345.TW', '2353.TW',
    '2360.TW', '2379.TW', '2395.TW', '2408.TW', '2412.TW', '2428.TW',
    '2431.TW', '2441.TW', '2453.TW', '2474.TW', '2491.TW', '2492.TW',
    '3016.TW', '3044.TW', '3081.TW', '3090.TW', '3105.TW', '3130.TW',
    '3149.TW', '3189.TW', '3231.TW', '3406.TW', '3443.TW', '3504.TW',
    '3529.TW', '3552.TW', '3570.TW', '3583.TW', '3615.TW', '3665.TW',
    '3682.TW', '3702.TW', '3706.TW', '4133.TW', '4551.TW', '4564.TW',
    '4726.TW', '4763.TW', '4766.TW', '4919.TW', '4938.TW',
    # ETF
    '0050.TW', '0056.TW', '00631L.TW', '00633L.TW', '00637L.TW',
    '00713.TW', '00757.TW', '00927.TW', '00937.TW',
]

results = []
errors = []

for sym in tw_stocks:
    try:
        tk = yf.Ticker(sym)
        hist = tk.history(period='3mo')
        if len(hist) < 10:
            errors.append(f'{sym}: only {len(hist)} rows')
            continue
        close = float(hist['Close'].iloc[-1])
        if close > 150:
            continue

        # RSI 14
        close_series = hist['Close']
        delta = close_series.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float('inf'))
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        # Momentum
        mom_1w = (close / float(hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0
        mom_1m = (close / float(hist['Close'].iloc[-20]) - 1) * 100 if len(hist) >= 20 else 0
        mom_3m = (close / float(hist['Close'].iloc[0]) - 1) * 100

        # MA
        ma5 = float(close_series.rolling(5).mean().iloc[-1])
        ma20 = float(close_series.rolling(20).mean().iloc[-1])
        ma60 = float(close_series.rolling(60).mean().iloc[-1]) if len(hist) >= 60 else None

        # Filters
        rsi_normal = 35 < rsi < 65
        has_momentum = mom_1m > 0
        ma_bull = ma5 > ma20 > ma60 if ma60 else ma5 > ma20

        if rsi_normal and has_momentum:
            results.append({
                'symbol': sym,
                'price': close,
                'rsi': rsi,
                'mom_1w': mom_1w,
                'mom_1m': mom_1m,
                'mom_3m': mom_3m,
                'ma_bull': ma_bull,
                'ma5': ma5,
                'ma20': ma20,
            })
    except Exception as e:
        errors.append(f'{sym}: {str(e)[:30]}')

results.sort(key=lambda x: x['mom_1m'], reverse=True)

print('\nTW Stocks < $150 with Positive Momentum + Normal RSI (35-65):')
print('=' * 70)
print(f"{'Symbol':<12} {'Price':>7} {'RSI':>5} {'1W':>6} {'1M':>6} {'3M':>7} MA")
print('-' * 70)
for r in results:
    ma = 'BULL' if r['ma_bull'] else 'N'
    print(f"{r['symbol']:<12} ${r['price']:>6.2f} {r['rsi']:>5.1f} {r['mom_1w']:>+5.1f}% {r['mom_1m']:>+5.1f}% {r['mom_3m']:>+6.1f}% {ma}")

print(f'\nTotal: {len(results)} stocks')
if errors:
    print(f'Errors/Skipped: {len(errors)}')
    for e in errors[:5]:
        print(f'  {e}')
