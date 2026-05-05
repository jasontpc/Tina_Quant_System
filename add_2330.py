# -*- coding: utf-8 -*-
"""Add 2330 to TW history database"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import sqlite3
import os
from datetime import datetime

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = os.path.join(BASE, "data")
DB = os.path.join(DATA_DIR, "tw_history.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Check if 2330 exists in stocks table
cur.execute("SELECT COUNT(*) FROM stocks WHERE symbol='2330'")
if cur.fetchone()[0] == 0:
    print("Adding 2330 to stocks table...")
    cur.execute("INSERT INTO stocks (symbol, name) VALUES ('2330', '台積電')")
else:
    print("2330 already in stocks table")

# Download historical data for 2330
print("Downloading 2330 history from yfinance...")
ticker = yf.Ticker("2330.TW")
df = ticker.history(start="2020-01-01", end=None)

if df.empty:
    print("ERROR: No data downloaded")
else:
    df = df.reset_index()
    df['Date'] = df['Date'].dt.tz_localize(None)
    
    rows_added = 0
    for _, row in df.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d')
        try:
            cur.execute('''INSERT OR REPLACE INTO daily_ohlcv 
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                ('2330', date_str, float(row['Open']), float(row['High']), 
                 float(row['Low']), float(row['Close']), int(row['Volume'])))
            rows_added += 1
        except Exception as e:
            print(f"Error inserting {date_str}: {e}")
    
    conn.commit()
    print(f"Added {rows_added} rows for 2330")

# Verify
cur.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE symbol='2330'")
print(f"2330 total rows: {cur.fetchone()[0]}")
cur.execute("SELECT MAX(date) FROM daily_ohlcv WHERE symbol='2330'")
print(f"2330 latest date: {cur.fetchone()[0]}")

conn.close()
print("Done!")