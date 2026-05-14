import yfinance as yf
import pandas as pd

# Check 00713 in multiple formats
for sym in ['00713.TW', '00713.TWO', '00713']:
    try:
        t = yf.Ticker(sym)
        h = t.history(period='5d')
        if len(h) > 0:
            close = h['Close'].iloc[-1]
            vol = h['Volume'].iloc[-1]
            print(f'{sym}: close={close:.2f} vol={vol}')
            break
    except Exception as e:
        print(f'{sym}: error {e}')