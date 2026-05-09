# Quick test: which Taiwan stocks have data in yfinance?
import yfinance as yf
import time

test_symbols = ['2330.TW', '2311.TW', '2884.TW', '0050.TW', '1101.TW']
for sym in test_symbols:
    try:
        t = yf.Ticker(sym)
        df = t.history(start='2024-01-01', end='2024-12-31', auto_adjust=True, timeout=5)
        print(f"{sym}: {len(df)} rows, cols={list(df.columns) if df is not None else None}")
    except Exception as e:
        print(f"{sym}: ERROR {e}")
    time.sleep(0.5)