# -*- coding: utf-8 -*-
"""Update US History DB with latest yfinance data"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import sqlite3
import os
from datetime import datetime, timedelta

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = os.path.join(BASE, "data")
DB = os.path.join(DATA_DIR, "us_history.db")

# Get last date in db
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT MAX(date) FROM daily_ohlcv")
last_date = cur.fetchone()[0]
print(f"Last date in DB: {last_date}")

# Get distinct symbols from db
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv LIMIT 100")
symbols = [r[0] for r in cur.fetchall()]
print(f"Symbols to update: {len(symbols)}")

# Update each symbol
updated = 0
errors = 0

for sym in symbols[:50]:  # Limit to 50 at a time to avoid rate limits
    try:
        ticker = yf.Ticker(sym)
        
        if last_date:
            start = (datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            start = '2020-01-01'
        
        df = ticker.history(start=start, end=None, period='5d')
        
        if df.empty:
            continue
            
        df = df.reset_index()
        df['Date'] = df['Date'].dt.tz_localize(None)
        
        for _, row in df.iterrows():
            date_str = row['Date'].strftime('%Y-%m-%d')
            cur.execute('''INSERT OR REPLACE INTO daily_ohlcv 
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (sym, date_str, float(row['Open']), float(row['High']), 
                 float(row['Low']), float(row['Close']), int(row['Volume'])))
        
        updated += 1
        print(f"  {sym}: {len(df)} rows added (last: {date_str})")
        
    except Exception as e:
        errors += 1
        print(f"  [X] {sym}: {e}")

conn.commit()

# Verify
cur.execute("SELECT MAX(date) FROM daily_ohlcv")
new_last = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM daily_ohlcv")
count = cur.fetchone()[0]
conn.close()

print(f"\n=== Update Complete ===")
print(f"Updated: {updated} symbols")
print(f"Errors: {errors}")
print(f"New last date: {new_last}")
print(f"Total rows: {count}")