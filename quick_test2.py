import yfinance as yf
import sqlite3
import time
from pathlib import Path

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
conn.close()

print(f"Existing: {len(existing)}")

# Try some US stocks NOT in DB
test_symbols = [
    'ABB','ABBV','ABC','ABT','ACN','ADBE','ADI','ADP','AEE','AEP',
    'AES','AFL','AGN','AIG','AIZ','AJG','ALGN','ALK','ALL','AME'
]

for sym in test_symbols:
    if sym in existing:
        print(f"  {sym}: already exists")
        continue
    try:
        t = yf.Ticker(sym)
        df = t.history(period='5d', auto_adjust=True)
        if df is not None and not df.empty and len(df) >= 2:
            print(f"  {sym}: OK ({len(df)} rows)")
        else:
            print(f"  {sym}: No data")
    except Exception as e:
        print(f"  {sym}: ERROR - {str(e)[:60]}")
    time.sleep(1.5)