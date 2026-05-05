import yfinance as yf
import sqlite3
import time
from pathlib import Path

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Get existing
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
conn.close()

print(f"Existing: {len(existing)}")
print(f"Testing 5 symbols...")

for sym in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']:
    if sym in existing:
        print(f"  {sym}: already exists, skip")
        continue
    try:
        t = yf.Ticker(sym)
        df = t.history(period='5d', auto_adjust=True)
        if df is not None and not df.empty:
            print(f"  {sym}: OK ({len(df)} rows)")
        else:
            print(f"  {sym}: No data")
    except Exception as e:
        print(f"  {sym}: ERROR - {e}")
    time.sleep(1)