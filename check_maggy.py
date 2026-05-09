import yfinance as yf

tickers = ['XOM', 'JNJ', 'XLE', 'EOG']
results = []

for t in tickers:
    try:
        yf_t = yf.Ticker(t)
        hist = yf_t.history(period='3mo')
        close = hist['Close'].values
        print(f'{t}: {len(close)} rows, last_close={close[-1]:.2f}')
        
        if len(close) >= 50:
            ma20 = sum(close[-20:]) / 20
            ma50 = sum(close[-50:]) / 50
            ma20_above = close[-1] > ma20
            ma20_vs_ma50 = ma20 > ma50
            
            # RSI calculation (14-period)
            period = 14
            gains = []
            losses = []
            for i in range(1, len(close)):
                diff = close[i] - close[i-1]
                if diff > 0:
                    gains.append(diff)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(diff))
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            rs = avg_gain / avg_loss if avg_loss > 0 else 999
            rsi = 100 - (100 / (1 + rs))
            
            results.append({
                'symbol': t,
                'price': close[-1],
                'ma20': ma20,
                'ma50': ma50,
                'ma20_above': ma20_above,
                'ma20_vs_ma50': ma20_vs_ma50,
                'rsi': rsi
            })
            print(f'  MA20={ma20:.2f}, MA50={ma50:.2f}, MA20 above price={ma20_above}, MA20>MA50={ma20_vs_ma50}, RSI={rsi:.1f}')
        else:
            print(f'  Not enough data: {len(close)} rows')
    except Exception as e:
        print(f'{t}: error - {e}')

print('\n--- Summary ---')
for r in results:
    cross = 'DEATH CROSS' if r['ma20_above'] == False and not r['ma20_vs_ma50'] else ('GOLDEN CROSS' if r['ma20_above'] and r['ma20_vs_ma50'] else 'NEUTRAL')
    print(f"{r['symbol']}: price={r['price']:.2f}, MA20={r['ma20']:.2f}, MA50={r['ma50']:.2f}, CROSS={cross}, RSI={r['rsi']:.1f}")