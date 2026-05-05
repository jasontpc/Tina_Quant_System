# Debug version - only test INTC and MCHP

CANDIDATE_STOCKS = ['INTC', 'MCHP']
import yfinance as yf
import pandas as pd
import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = f'{DATA_DIR}\\us_value_growth.db'
BASE_PRICE_MAX = 100

def calc_rsi(prices, period=14):
    if len(prices) < period:
        return None
    delta = pd.Series(prices).diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return float((100 - (100 / (1 + rs))).iloc[-1])

for sym in CANDIDATE_STOCKS:
    print(f'=== Processing {sym} ===')
    try:
        t = yf.Ticker(sym)
        h = t.history(period='6mo')
        print(f'  History rows: {len(h)}')
        
        if h is None or h.empty or len(h) < 30:
            print(f'  FAIL: insufficient data')
            continue
        
        price = float(h['Close'].iloc[-1])
        vol_today = int(h['Volume'].iloc[-1])
        vol_avg5 = int(h['Volume'].rolling(5).mean().iloc[-1])
        vol_avg20 = int(h['Volume'].rolling(20).mean().iloc[-1])
        print(f'  Price: {price}, vol_today: {vol_today:,}')
        
        if price >= BASE_PRICE_MAX:
            print(f'  FAIL: price {price} >= {BASE_PRICE_MAX}')
            continue
        
        c = h['Close'].reset_index(drop=True)
        print(f'  Close series len: {len(c)}')
        
        rsi14 = calc_rsi(c.values, 14)
        ma5 = float(c.rolling(5).mean().iloc[-1])
        ma20 = float(c.rolling(20).mean().iloc[-1])
        ma60 = float(c.rolling(60).mean().iloc[-1]) if len(c) >= 60 else ma20
        bias20 = (price / ma20 - 1) * 100
        print(f'  RSI: {rsi14}, MA20: {ma20}, BIAS20: {bias20:.2f}%')
        
        vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 0
        print(f'  vol_ratio: {vol_ratio:.2f} (today {vol_today:,} / avg20 {vol_avg20:,})')
        
        tech_pass = (30 <= rsi14 <= 70 and bias20 < 15 and vol_ratio >= 0.5)
        print(f'  tech_pass: {tech_pass}')
        
        print(f'  PASSED: returning data')
        
    except Exception as e:
        print(f'  EXCEPTION: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

print()
print('=== Script analysis complete ===')