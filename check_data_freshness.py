# -*- coding: utf-8 -*-
"""Check data freshness"""
import yfinance as yf
import sqlite3
import os
from datetime import datetime

base = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"

# Check TW history
db1 = os.path.join(base, "data", "tw_history.db")
conn1 = sqlite3.connect(db1)
cur1 = conn1.cursor()
cur1.execute("SELECT MAX(date) FROM daily_ohlcv")
tw_last = cur1.fetchone()[0]
cur1.execute("SELECT COUNT(*) FROM daily_ohlcv")
tw_count = cur1.fetchone()[0]
conn1.close()

# Check US history
db2 = os.path.join(base, "data", "us_history.db")
conn2 = sqlite3.connect(db2)
cur2 = conn2.cursor()
cur2.execute("SELECT MAX(date) FROM daily_ohlcv")
us_last = cur2.fetchone()[0]
cur2.execute("SELECT COUNT(*) FROM daily_ohlcv")
us_count = cur2.fetchone()[0]
conn2.close()

# Check ETF history
db3 = os.path.join(base, "data", "etf_history.db")
conn3 = sqlite3.connect(db3)
cur3 = conn3.cursor()
cur3.execute("SELECT MAX(date) FROM daily_ohlcv")
etf_last = cur3.fetchone()[0]
conn3.close()

today = datetime.now().strftime('%Y-%m-%d')

print("=== Data Freshness Check ===")
print(f"TW History: {tw_count} rows, last date: {tw_last}")
print(f"US History: {us_count} rows, last date: {us_last}")
print(f"ETF History: last date: {etf_last}")
print(f"Today: {today}")
print()

# Check yfinance for latest 2330
print("=== yfinance Live Check (2330.TW) ===")
try:
    df = yf.download("2330.TW", period="5d", progress=False)
    if not df.empty:
        last_close = df['Close'].iloc[-1]
        last_date = df.index[-1].strftime('%Y-%m-%d')
        print(f"2330.TW yfinance: date={last_date}, close={last_close}")
except Exception as e:
    print(f"Error: {e}")

# Check yfinance for SPY
print()
print("=== yfinance Live Check (SPY) ===")
try:
    df = yf.download("SPY", period="5d", progress=False)
    if not df.empty:
        last_close = df['Close'].iloc[-1]
        last_date = df.index[-1].strftime('%Y-%m-%d')
        print(f"SPY yfinance: date={last_date}, close={last_close}")
except Exception as e:
    print(f"Error: {e}")

print()
print("=== Gap Analysis ===")
if tw_last and tw_last < today:
    print(f"[!] TW History is STALE by {today} - {tw_last}")
else:
    print(f"[OK] TW History is up to date")
    
if us_last and us_last < today:
    print(f"[!] US History is STALE by {today} - {us_last}")
else:
    print(f"[OK] US History is up to date")